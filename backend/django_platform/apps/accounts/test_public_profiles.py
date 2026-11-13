from contextlib import ExitStack
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.billing.access import has_access
from apps.billing.models import Checkout, Subscription
from apps.communications.models import NewsletterPreference
from apps.editorial.models import EditorialGroup, Membership
from .models import Profile


def photo(width=600, height=800):
    output = BytesIO()
    Image.new("RGB", (width, height), "#9f7135").save(output, "PNG")
    return SimpleUploadedFile("foto.png", output.getvalue(), content_type="image/png")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_HOST="smtp.example.invalid", DEFAULT_FROM_EMAIL="contato@example.test")
class PublicProfileTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temporary = TemporaryDirectory()
        cls.patches = ExitStack()
        cls.patches.enter_context(patch.object(Profile._meta.get_field("avatar"), "storage", FileSystemStorage(location=cls.temporary.name)))

    @classmethod
    def tearDownClass(cls):
        cls.patches.close()
        cls.temporary.cleanup()
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.developer = users.objects.create_superuser(username="profile-dev", email="dev-profile@example.invalid", password="PublicProfile!81-Password")
        cls.coordinator = users.objects.create_user(username="profile-coordinator", email="coord-profile@example.invalid", password="PublicProfile!81-Password")
        cls.auxiliary = users.objects.create_user(username="profile-auxiliary", email="aux-profile@example.invalid", password="PublicProfile!81-Password")
        cls.reader = users.objects.create_user(username="profile-reader", email="reader-profile@example.invalid", password="PublicProfile!81-Password")
        cls.inactive = users.objects.create_user(username="profile-inactive", email="inactive-profile@example.invalid", is_active=False)
        cls.group = EditorialGroup.objects.create(name="Equipe", slug="public-profiles-team")
        Membership.objects.create(user=cls.coordinator, group=cls.group, role="coordinator")
        Membership.objects.create(user=cls.auxiliary, group=cls.group, role="columnist")
        for user, name in [(cls.developer, "Pessoa desenvolvedora"), (cls.coordinator, "Pessoa coordenadora"), (cls.auxiliary, "Pessoa auxiliar"), (cls.reader, "Pessoa assinante")]:
            user.profile.display_name = name
            user.profile.save()

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self, user=None):
        self.client.force_login(user or self.reader)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def update(self, data, multipart=False):
        return self.client.patch("/api/auth/me", data, format="multipart" if multipart else "json", HTTP_X_CSRFTOKEN=self.token)

    def public(self, user):
        return self.client.get(f"/api/profiles/{user.profile.public_id}")

    def request_email(self, email="new-profile@example.invalid", password="PublicProfile!81-Password"):
        return self.client.post("/api/auth/email", {"new_email": email, "current_password": password}, format="json", HTTP_X_CSRFTOKEN=self.token)

    def confirm(self, token):
        return self.client.post("/api/auth/email/confirm", {"token": token}, format="json", HTTP_X_CSRFTOKEN=self.token)

    def email_token(self):
        return mail.outbox[-1].body.split("#token=")[1].split()[0]

    def test_all_active_profiles_are_public_and_private_account_data_is_absent(self):
        data = self.client.get("/api/profiles").json()
        self.assertEqual(data["count"], 4)
        self.assertEqual(set(self.public(self.reader).json()), {"public_id", "display_name", "avatar_url", "role", "role_label", "biography", "website", "phone", "video_embed_url"})
        self.assertNotIn(self.reader.email, str(data))
        for forbidden in ["password", "username", "pending_email", "email_change_hash", "is_superuser", "subscription_status"]:
            self.assertNotIn(forbidden, str(data))
        self.assertEqual(self.public(self.inactive).status_code, 404)
        self.assertEqual(len(set(Profile.objects.values_list("public_id", flat=True))), Profile.objects.count())

    def test_role_labels_are_derived_and_cannot_be_edited(self):
        for user, code, label in [(self.developer, "developer", "Desenvolvedor"), (self.coordinator, "coordinator", "Coordenador"), (self.auxiliary, "auxiliary", "Auxiliar"), (self.reader, "subscriber", "Assinante")]:
            self.assertEqual(self.public(user).json()["role_label"], label)
            filtered = self.client.get("/api/profiles?role=" + code).json()
            self.assertEqual(filtered["count"], 1)
            self.login(user)
            self.assertEqual(self.update({"profile_role": "developer"}).status_code, 400)
        self.assertEqual(self.client.get("/api/profiles?role=invalid").status_code, 400)

    def test_subscriber_updates_only_own_public_presentation(self):
        self.login()
        response = self.update({"display_name": "Novo nome", "biography": "Minha caminhada\nEm comunidade", "website": "https://example.org", "video_url": "https://youtu.be/abcdefghijk"})
        self.assertEqual(response.status_code, 200, response.content)
        public = self.public(self.reader).json()
        self.assertEqual(public["display_name"], "Novo nome")
        self.assertEqual(public["biography"], "Minha caminhada\nEm comunidade")
        self.assertEqual(public["video_embed_url"], "https://www.youtube-nocookie.com/embed/abcdefghijk")
        self.assertEqual(self.public(self.auxiliary).json()["biography"], "")
        self.reader.refresh_from_db()
        self.assertFalse(self.reader.is_superuser)
        self.assertFalse(self.reader.is_staff)

    def test_phone_is_available_only_to_developer_and_current_coordinator(self):
        for user in [self.reader, self.auxiliary]:
            self.login(user)
            self.assertEqual(self.update({"phone": "11999999999"}).status_code, 403)
            self.assertFalse(self.client.get("/api/auth/me").json()["can_publish_phone"])
        for user in [self.developer, self.coordinator]:
            self.login(user)
            self.assertEqual(self.update({"phone": "+55 (11) 99999-9999"}).status_code, 200)
            self.assertEqual(self.public(user).json()["phone"], "+55 (11) 99999-9999")
        Membership.objects.filter(user=self.coordinator).delete()
        self.assertEqual(self.public(self.coordinator).json()["phone"], "")
        self.assertEqual(self.public(self.coordinator).json()["role"], "subscriber")

    def test_upload_replace_remove_and_private_storage_guard(self):
        self.login()
        response = self.update({"avatar": photo()}, multipart=True)
        self.assertEqual(response.status_code, 200, response.content)
        first = response.json()["avatar_url"]
        self.reader.profile.refresh_from_db()
        with Image.open(self.reader.profile.avatar.path) as image:
            self.assertEqual(image.size, (512, 512))
            self.assertEqual(image.format, "WEBP")
            self.assertFalse(image.getexif())
        self.client.logout()
        self.assertEqual(self.client.get(first).status_code, 200)
        self.assertEqual(self.client.get("/media/" + self.reader.profile.avatar.name).status_code, 404)
        self.login()
        second = self.update({"avatar": photo(800, 600)}, multipart=True).json()["avatar_url"]
        self.assertNotEqual(first, second)
        self.assertEqual(self.update({"remove_avatar": True}).status_code, 200)
        self.assertEqual(self.client.get(second).status_code, 404)
        self.assertIsNone(self.public(self.reader).json()["avatar_url"])

    def test_invalid_photos_are_rejected(self):
        self.login()
        invalid = [photo(199, 300), photo(300, 199), photo(4097, 300), SimpleUploadedFile("fake.jpg", b"not-a-photo", content_type="image/jpeg"), SimpleUploadedFile("large.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")]
        for image in invalid:
            self.assertEqual(self.update({"avatar": image}, multipart=True).status_code, 400)
        self.assertEqual(self.update({"avatar": photo(), "remove_avatar": True}, multipart=True).status_code, 400)

    def test_inactive_profile_and_photo_are_unavailable(self):
        self.login()
        image = self.update({"avatar": photo()}, multipart=True).json()["avatar_url"]
        self.reader.is_active = False
        self.reader.save()
        self.assertEqual(self.public(self.reader).status_code, 404)
        self.assertEqual(self.client.get(image).status_code, 404)

    def test_video_website_and_phone_are_validated(self):
        self.login(self.developer)
        for values in [{"video_url": "https://youtube.com.evil.invalid/watch?v=abcdefghijk"}, {"website": "javascript:alert(1)"}, {"website": "https://user:password@example.org"}, {"phone": "<script>test</script>"}]:
            self.assertEqual(self.update(values).status_code, 400)

    def test_directory_search_never_searches_by_email(self):
        self.assertEqual(self.client.get("/api/profiles?q=assinante").json()["count"], 1)
        self.assertEqual(self.client.get("/api/profiles?q=reader-profile@example.invalid").json()["count"], 0)

    def test_email_change_requires_password_csrf_and_unique_address(self):
        self.login()
        self.assertEqual(self.request_email(password="wrong").status_code, 400)
        self.assertEqual(self.request_email(email=self.auxiliary.email).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/email", {"new_email": "new@example.invalid", "current_password": "PublicProfile!81-Password"}, format="json").status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_change_preserves_old_login_until_single_use_confirmation(self):
        self.login()
        self.assertEqual(self.request_email().status_code, 200)
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.email, "reader-profile@example.invalid")
        self.assertIsNotNone(authenticate(email=self.reader.email, password="PublicProfile!81-Password"))
        token = self.email_token()
        self.assertNotEqual(self.reader.profile.email_change_hash, token)
        self.assertEqual(self.confirm(token).status_code, 200)
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.email, "new-profile@example.invalid")
        self.assertIsNotNone(authenticate(email=self.reader.email, password="PublicProfile!81-Password"))
        self.assertIsNone(authenticate(email="reader-profile@example.invalid", password="PublicProfile!81-Password"))
        self.assertEqual(self.confirm(token).status_code, 400)
        self.assertNotIn("new-profile@example.invalid", str(self.public(self.reader).json()))

    def test_email_link_expiry_and_password_change_invalidate_confirmation(self):
        self.login()
        self.request_email()
        token = self.email_token()
        Profile.objects.filter(user=self.reader).update(email_change_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.confirm(token).status_code, 400)
        self.request_email()
        token = self.email_token()
        self.reader.set_password("NewProfilePassword!81")
        self.reader.save()
        self.assertEqual(self.confirm(token).status_code, 400)

    def test_conflict_created_after_request_does_not_replace_another_account(self):
        self.login()
        self.request_email()
        token = self.email_token()
        get_user_model().objects.create_user(username="profile-conflict", email="new-profile@example.invalid")
        self.assertEqual(self.confirm(token).status_code, 400)
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.email, "reader-profile@example.invalid")

    def test_changing_email_preserves_paid_period_and_updates_newsletter_identity_safely(self):
        checkout = Checkout.objects.create(legal_version="test")
        Subscription.objects.create(user=self.reader, email=self.reader.email, checkout=checkout, provider_id="profile-subscription", paid_until=timezone.now() + timedelta(days=10))
        previous = NewsletterPreference.objects.create(user=self.reader, email=self.reader.email, opted_in=True)
        new_preference = NewsletterPreference.objects.create(email="new-profile@example.invalid", opted_in=True)
        self.login()
        self.request_email()
        self.assertEqual(self.confirm(self.email_token()).status_code, 200)
        self.reader.refresh_from_db()
        self.assertTrue(has_access(self.reader))
        previous.refresh_from_db()
        self.assertIsNone(previous.user)
        self.assertFalse(previous.opted_in)
        self.assertTrue(self.client.get("/api/newsletter/preference").json()["opted_in"])
        new_preference.refresh_from_db()
        self.assertEqual(new_preference.user_id, self.reader.pk)

    @override_settings(EMAIL_HOST="")
    def test_unavailable_email_delivery_does_not_change_account_or_create_pending_request(self):
        self.login()
        self.assertEqual(self.request_email().status_code, 503)
        self.reader.profile.refresh_from_db()
        self.assertEqual(self.reader.profile.pending_email, "")

    def test_failed_mail_does_not_leave_a_pending_change(self):
        self.login()
        with patch("apps.accounts.email_views.send_mail", side_effect=RuntimeError("smtp")):
            self.assertEqual(self.request_email().status_code, 503)
        self.reader.profile.refresh_from_db()
        self.assertEqual(self.reader.profile.pending_email, "")
