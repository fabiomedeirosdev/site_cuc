from contextlib import ExitStack
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.billing.models import Checkout, Subscription
from apps.editorial.models import EditorialGroup, Membership
from .models import Campaign, Delivery, NewsletterPreference, NewsletterSettings, Notice
from .services import digest_content, render_campaign, run_newsletters


def photo(width=1200, height=1600):
    output = BytesIO()
    Image.new("RGB", (width, height), "#bc9245").save(output, "PNG")
    return SimpleUploadedFile("cartaz.png", output.getvalue(), content_type="image/png")


@override_settings(DEBUG=True, NEWSLETTER_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CommunicationImagesAudienceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temporary = TemporaryDirectory()
        cls.patches = ExitStack()
        storage = FileSystemStorage(location=cls.temporary.name)
        for model in [Notice, Campaign, NewsletterSettings]:
            cls.patches.enter_context(patch.object(model._meta.get_field("image"), "storage", storage))

    @classmethod
    def tearDownClass(cls):
        cls.patches.close()
        cls.temporary.cleanup()
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.coordinator = users.objects.create_user(username="audience-coordinator", email="coord-audience@example.invalid")
        cls.reader = users.objects.create_user(username="audience-reader", email="reader-audience@example.invalid")
        cls.expired = users.objects.create_user(username="audience-expired", email="expired-audience@example.invalid")
        cls.unconsented = users.objects.create_user(username="audience-unconsented", email="unconsented-audience@example.invalid")
        cls.group = EditorialGroup.objects.create(name="Comunicação", slug="communication-images")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        cls.checkout = Checkout.objects.create(legal_version="test")

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def create(self, kind="notices", **fields):
        defaults = {"title": "Retiro", "body": "Detalhes reservados", "is_published": True} if kind == "notices" else {"subject": "Convite ao retiro", "introduction": "Nossa programação"}
        return self.client.post(f"/api/communications/{kind}", {**defaults, **fields}, format="multipart", HTTP_X_CSRFTOKEN=self.token)

    def patch(self, kind, pk, **fields):
        return self.client.patch(f"/api/communications/{kind}/{pk}", fields, format="multipart", HTTP_X_CSRFTOKEN=self.token)

    def subscription(self, user, days=10, opted=True, status="ACTIVE"):
        subscription = Subscription.objects.create(user=user, email=user.email, checkout=self.checkout, provider_id=f"images-{user.pk}", status=status, paid_until=timezone.now() + timedelta(days=days))
        preference = NewsletterPreference.objects.create(user=user, email=user.email, opted_in=opted)
        return subscription, preference

    def scheduled_campaign(self, **fields):
        return Campaign.objects.create(subject="Nossa semana", introduction="Convite", status="scheduled", scheduled_at=timezone.now() - timedelta(minutes=1), created_by=self.coordinator, **fields)

    def test_notice_upload_preserves_portrait_and_uses_guarded_url(self):
        self.login(self.coordinator)
        response = self.create(image=photo(), image_alt="Cartaz do retiro")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["image_url"], f"/api/communication-images/notices/{data['id']}")
        notice = Notice.objects.get(pk=data["id"])
        with Image.open(notice.image.path) as image:
            self.assertEqual(image.size, (1200, 1600))
            self.assertEqual(image.format, "JPEG")
            self.assertFalse(image.getexif())
        self.client.logout()
        self.assertEqual(self.client.get(data["image_url"]).status_code, 200)
        self.assertEqual(self.client.get("/media/" + notice.image.name).status_code, 404)

    def test_private_notice_hides_body_image_and_alt_and_guards_previously_public_url(self):
        self.login(self.coordinator)
        data = self.create(image=photo(), image_alt="Texto confidencial no cartaz").json()
        self.assertEqual(self.patch("notices", data["id"], is_members_only=True).status_code, 200)
        self.client.logout()
        response = self.client.get("/api/mural")
        item = response.json()["results"][0]
        self.assertTrue(item["is_locked"])
        self.assertIsNone(item["body"])
        self.assertIsNone(item["image_url"])
        self.assertEqual(item["image_alt"], "")
        self.assertNotIn("Detalhes reservados", response.content.decode())
        self.assertEqual(self.client.get(data["image_url"]).status_code, 404)
        self.assertIn("no-store", response["Cache-Control"])
        subscription, _ = self.subscription(self.reader)
        self.login(self.reader)
        self.assertEqual(self.client.get("/api/mural").json()["results"][0]["body"], "Detalhes reservados")
        self.assertEqual(self.client.get(data["image_url"]).status_code, 200)
        subscription.safety_hold = True
        subscription.save()
        self.assertEqual(self.client.get(data["image_url"]).status_code, 404)

    def test_drafts_and_weekly_images_are_never_public(self):
        self.login(self.coordinator)
        data = self.create(is_published=False, image=photo(), image_alt="Rascunho").json()
        self.assertEqual(self.client.get(data["image_url"]).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(data["image_url"]).status_code, 404)

    def test_only_authorized_team_can_upload_and_csrf_is_required(self):
        self.login(self.reader)
        self.assertEqual(self.create(image=photo(), image_alt="Foto").status_code, 403)
        self.login(self.coordinator)
        self.assertEqual(self.client.post("/api/communications/notices", {"title": "Aviso", "body": "Texto"}, format="json").status_code, 403)

    def test_invalid_uploads_and_missing_alt_are_rejected(self):
        self.login(self.coordinator)
        for upload in [photo(599, 400), photo(600, 299), photo(4097, 300), SimpleUploadedFile("fake.jpg", b"fake", content_type="image/jpeg"), SimpleUploadedFile("huge.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")]:
            self.assertEqual(self.create(image=upload, image_alt="Descrição").status_code, 400)
        self.assertEqual(self.create(image=photo()).status_code, 400)

    def test_replace_remove_image_and_change_visibility(self):
        self.login(self.coordinator)
        data = self.create(image=photo(), image_alt="Original", is_members_only=True).json()
        original = Notice.objects.get(pk=data["id"]).image.name
        response = self.patch("notices", data["id"], image=photo(1600, 900), image_alt="Nova imagem", is_members_only=False)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotEqual(Notice.objects.get(pk=data["id"]).image.name, original)
        self.assertEqual(self.patch("notices", data["id"], remove_image=True).status_code, 200)
        self.client.logout()
        item = self.client.get("/api/mural").json()["results"][0]
        self.assertFalse(item["is_locked"])
        self.assertIsNone(item["image_url"])

    def test_preview_embeds_unsaved_image_without_publishing_or_sending(self):
        self.login(self.coordinator)
        response = self.client.post("/api/communications/preview", {"subject": "Retiro", "introduction": "<script>unsafe</script>", "image": photo(), "image_alt": "Cartaz", "is_members_only": True}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.content)
        html = response.json()["html"]
        self.assertIn("data:image/jpeg;base64,", html)
        self.assertIn("Edição exclusiva para assinantes", html)
        self.assertNotIn("<script>", html)
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_saved_campaign_preview_retains_image(self):
        self.login(self.coordinator)
        data = self.create("campaigns", image=photo(), image_alt="Cartaz").json()
        response = self.client.post("/api/communications/preview", {"campaign_id": data["id"], "subject": "Prévia atualizada", "introduction": "Mensagem"}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("data:image/jpeg;base64,", response.json()["html"])

    def test_members_campaign_sends_only_to_consented_current_paid_accounts(self):
        self.subscription(self.reader, status="CANCELED")
        self.subscription(self.expired, days=-1)
        self.subscription(self.unconsented, opted=False)
        NewsletterPreference.objects.create(email="visitor@example.invalid", opted_in=True)
        self.scheduled_campaign(is_members_only=True)
        self.assertEqual(run_newsletters()["sent"], 1)
        self.assertEqual(mail.outbox[0].to, [self.reader.email])
        self.assertEqual(Delivery.objects.count(), 1)

    def test_public_campaign_includes_consented_visitors_and_expired_accounts(self):
        self.subscription(self.reader)
        self.subscription(self.expired, days=-1)
        NewsletterPreference.objects.create(email="visitor@example.invalid", opted_in=True)
        self.scheduled_campaign()
        self.assertEqual(run_newsletters()["sent"], 3)

    def test_subscription_rechecked_before_retry(self):
        subscription, _ = self.subscription(self.reader)
        self.scheduled_campaign(is_members_only=True)
        with patch("apps.communications.services.send_mail", side_effect=RuntimeError("smtp")):
            self.assertEqual(run_newsletters()["failed"], 1)
        subscription.paid_until = timezone.now() - timedelta(seconds=1)
        subscription.save()
        self.assertEqual(run_newsletters()["sent"], 0)
        self.assertEqual(Delivery.objects.get().status, "skipped")

    def test_campaign_image_is_inline_in_actual_email(self):
        self.subscription(self.reader)
        self.login(self.coordinator)
        data = self.create("campaigns", image=photo(), image_alt="Cartaz do evento", is_members_only=True).json()
        campaign = Campaign.objects.get(pk=data["id"])
        campaign.status = "scheduled"
        campaign.scheduled_at = timezone.now() - timedelta(minutes=1)
        campaign.save()
        self.assertEqual(run_newsletters()["sent"], 1)
        message = mail.outbox[0]
        self.assertIn("cid:newsletter-hero", message.alternatives[0].content)
        self.assertEqual(message.attachments[0]["Content-ID"], "<newsletter-hero>")
        self.assertEqual(message.attachments[0].get_content_type(), "image/jpeg")
        self.client.logout()
        self.assertEqual(self.client.get(data["image_url"]).status_code, 404)

    def test_public_newsletter_revalidates_private_notice_snapshot(self):
        notice = Notice.objects.create(title="Aviso", body="Segredo", is_published=True, created_by=self.coordinator)
        campaign = Campaign(subject="Novidades", introduction="Mensagem", snapshot=digest_content())
        notice.is_members_only = True
        notice.save()
        html = render_campaign(campaign)
        self.assertNotIn("Segredo", html)
        self.assertIn("Aviso exclusivo para assinantes", html)

    def test_weekly_campaign_copies_audience_and_image(self):
        self.login(self.coordinator)
        response = self.client.put("/api/communications/weekly", {"weekly_enabled": True, "weekday": 0, "hour": 0, "subject": "Boletim", "introduction": "Novidades", "is_members_only": True, "image": photo(), "image_alt": "Cartaz semanal"}, format="multipart", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.subscription(self.reader)
        run_newsletters()
        campaign = Campaign.objects.get()
        config = NewsletterSettings.objects.get()
        self.assertTrue(campaign.is_members_only)
        self.assertEqual(campaign.image.name, config.image.name)
        self.assertEqual(campaign.image_alt, "Cartaz semanal")
        self.client.logout()
        self.assertEqual(self.client.get(response.json()["image_url"]).status_code, 404)
