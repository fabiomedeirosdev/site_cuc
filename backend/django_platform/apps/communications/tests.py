import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Checkout, Subscription
from apps.editorial.models import EditorialGroup, Membership
from .models import Campaign, Delegation, Delivery, Event, NewsletterPreference, NewsletterSettings, Notice
from .policies import can_manage
from .services import render_campaign, request_confirmation, run_newsletters


@override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", NEWSLETTER_ENABLED=True, PUBLIC_FRONTEND_URL="https://example.invalid")
class CommunicationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.coordinator = User.objects.create_user(username="coord", email="coord@example.invalid", password="LocalCommunicationTest!81")
        cls.helper = User.objects.create_user(username="helper", email="helper@example.invalid", password="LocalCommunicationTest!81")
        cls.outsider = User.objects.create_user(username="outside", email="outside@example.invalid", password="LocalCommunicationTest!81")
        cls.group = EditorialGroup.objects.create(name="Comunicação teste", slug="communication-test")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        Membership.objects.create(group=cls.group, user=cls.helper, role="columnist")
        cls.checkout = Checkout.objects.create(legal_version="test")

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.client = APIClient(enforce_csrf_checks=True)
        self.now = timezone.now()

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def write(self, method, path, data):
        return getattr(self.client, method)(path, data, format="json", HTTP_X_CSRFTOKEN=self.token)

    def subscriber(self, user, opted=True, days=10, status="ACTIVE"):
        subscription = Subscription.objects.create(checkout=self.checkout, provider_id=f"SUBS_test_{user.pk}", email=user.email, user=user, paid_until=self.now + timedelta(days=days), status=status)
        preference = NewsletterPreference.objects.create(user=user, opted_in=opted)
        return subscription, preference

    def campaign(self):
        return Campaign.objects.create(subject="Novidades", introduction="Nossa semana", status="scheduled", scheduled_at=self.now - timedelta(minutes=1), created_by=self.coordinator)

    def test_only_application_admin_can_delegate_to_active_facilitator(self):
        self.login(self.coordinator)
        self.assertEqual(self.write("put", "/api/communications/delegation", {"facilitator": self.helper.pk}).status_code, 403)
        founder = get_user_model().objects.create_user(username="founder-delegate", email="founder-delegate@example.invalid")
        founder.profile.community_role = "founder"
        founder.profile.save()
        self.login(founder)
        self.assertEqual(self.write("put", "/api/communications/delegation", {"facilitator": self.outsider.pk, "can_edit_agenda": True, "can_edit_mural": False}).status_code, 404)
        self.assertEqual(self.write("put", "/api/communications/delegation", {"facilitator": self.helper.pk, "can_edit_agenda": True, "can_edit_mural": False}).status_code, 200)
        self.assertTrue(can_manage(self.helper))
        self.login(self.helper)
        self.assertEqual(self.write("put", "/api/communications/delegation", {"facilitator": self.outsider.pk}).status_code, 403)
        self.helper.refresh_from_db()
        self.assertFalse(self.helper.is_staff)
        self.assertFalse(self.helper.is_superuser)

    def test_removing_delegation_membership_or_coordinator_revokes_access_immediately(self):
        delegation = Delegation.objects.create(coordinator=self.coordinator, facilitator=self.helper)
        self.login(self.helper)
        self.assertEqual(self.client.get("/api/communications/events").status_code, 200)
        Membership.objects.filter(user=self.helper).update(role="columnist")
        delegation.delete()
        self.assertEqual(self.client.get("/api/communications/events").status_code, 403)
        Delegation.objects.create(coordinator=self.coordinator, facilitator=self.helper)
        Membership.objects.filter(user=self.coordinator).delete()
        self.assertFalse(can_manage(self.helper))

    def test_plain_staff_and_ordinary_facilitator_cannot_manage_communications(self):
        self.outsider.is_staff = True
        self.outsider.save()
        for user in [self.outsider, self.helper]:
            self.login(user)
            self.assertEqual(self.client.get("/api/communications/events").status_code, 403)

    def test_event_draft_publish_update_cancel_and_delete_are_reflected_in_mural(self):
        self.login(self.coordinator)
        data = {"title": "Encontro", "description": "Partilha", "starts_at": (self.now + timedelta(days=2)).isoformat(), "location": "Salão"}
        created = self.write("post", "/api/communications/events", data)
        self.assertEqual(created.status_code, 201)
        pk = created.json()["id"]
        self.assertEqual(self.client.get("/api/mural").json()["count"], 0)
        self.assertEqual(self.write("patch", f"/api/communications/events/{pk}", {"is_published": True, "title": "Novo encontro"}).status_code, 200)
        self.assertEqual(self.client.get("/api/mural").json()["results"][0]["title"], "Novo encontro")
        self.write("patch", f"/api/communications/events/{pk}", {"is_cancelled": True})
        self.assertTrue(self.client.get("/api/events").json()["results"][0]["is_cancelled"])
        self.write("delete", f"/api/communications/events/{pk}", {})
        self.assertEqual(self.client.get("/api/mural").json()["count"], 0)

    def test_event_validation_and_author_cannot_be_spoofed(self):
        self.login(self.coordinator)
        data = {"title": "Encontro", "description": "Partilha", "starts_at": self.now.isoformat(), "ends_at": (self.now - timedelta(minutes=1)).isoformat(), "location": "Salão"}
        self.assertEqual(self.write("post", "/api/communications/events", data).status_code, 400)
        data.pop("ends_at")
        self.assertEqual(self.write("post", "/api/communications/events", {**data, "created_by": self.outsider.pk}).status_code, 400)
        self.assertEqual(self.client.post("/api/communications/events", data, format="json").status_code, 403)

    def test_public_archive_contains_finished_but_not_ongoing_or_draft_events(self):
        for title, start, end, published in [("Passado", -2, -1, True), ("Em andamento", -1, 1, True), ("Rascunho", 1, 2, False)]:
            Event.objects.create(title=title, description="Descrição", location="Sede", starts_at=self.now + timedelta(days=start), ends_at=self.now + timedelta(days=end), is_published=published, created_by=self.coordinator)
        self.assertEqual(self.client.get("/api/events").json()["results"][0]["title"], "Em andamento")
        self.assertEqual(self.client.get("/api/events?past=1").json()["results"][0]["title"], "Passado")

    def test_notice_requires_publication_and_is_editable_by_selected_helper(self):
        Delegation.objects.create(coordinator=self.coordinator, facilitator=self.helper)
        self.login(self.helper)
        result = self.write("post", "/api/communications/notices", {"title": "Aviso", "body": "Informação", "is_published": True})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(self.client.get("/api/mural").json()["results"][0]["kind"], "notice")

    def test_newsletter_sends_once_to_consented_readers_even_after_paid_period_expires(self):
        self.subscriber(self.coordinator)
        self.subscriber(self.helper, opted=False)
        self.subscriber(self.outsider, days=-1)
        campaign = self.campaign()
        self.assertEqual(run_newsletters()["sent"], 2)
        self.assertEqual(run_newsletters()["sent"], 0)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual({message.to[0] for message in mail.outbox}, {self.coordinator.email, self.outsider.email})
        self.assertIn("Deixar de receber", mail.outbox[0].alternatives[0].content)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, "sent")

    def test_canceled_but_paid_subscriber_remains_eligible(self):
        self.subscriber(self.helper, status="CANCELED", days=1)
        self.campaign()
        self.assertEqual(run_newsletters()["sent"], 1)

    def test_unsubscribed_recipient_is_skipped_at_delivery(self):
        subscription, preference = self.subscriber(self.helper)
        campaign = self.campaign()
        with patch("apps.communications.services.send_mail", side_effect=RuntimeError("smtp")):
            self.assertEqual(run_newsletters()["failed"], 1)
        preference.opted_in = False
        preference.save()
        self.assertEqual(run_newsletters()["sent"], 0)
        self.assertEqual(Delivery.objects.get().status, "skipped")
        self.assertEqual(len(mail.outbox), 0)

    def test_failed_smtp_is_retried_without_resending_successful_deliveries(self):
        self.subscriber(self.helper)
        self.campaign()
        with patch("apps.communications.services.send_mail", side_effect=RuntimeError("smtp")):
            self.assertEqual(run_newsletters()["failed"], 1)
        self.assertEqual(run_newsletters()["sent"], 1)
        self.assertEqual(run_newsletters()["sent"], 0)
        self.assertEqual(Delivery.objects.get().attempts, 2)

    def test_newsletter_html_escapes_editor_text_and_contains_current_agenda(self):
        campaign = Campaign(subject="<script>test</script>", introduction="<img src=x onerror=alert(1)>")
        Event.objects.create(title="Encontro", description="Partilha", location="Sede", starts_at=self.now + timedelta(days=2), is_published=True, created_by=self.coordinator)
        html = render_campaign(campaign)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("Encontro", html)
        self.assertIn("agenda.html", html)

    def test_weekly_monday_at_nine_brasilia_and_same_week_deduplication(self):
        NewsletterSettings.objects.create(weekly_enabled=True, updated_by=self.coordinator)
        monday = datetime(2026, 11, 16, 8, 59, tzinfo=ZoneInfo("America/Sao_Paulo"))
        with patch("django.utils.timezone.now", return_value=monday):
            run_newsletters()
        self.assertEqual(Campaign.objects.count(), 0)
        with patch("django.utils.timezone.now", return_value=monday.replace(hour=9, minute=0)):
            run_newsletters()
            run_newsletters()
        self.assertEqual(Campaign.objects.count(), 1)

    @override_settings(NEWSLETTER_ENABLED=False)
    def test_disabled_delivery_cannot_contact_smtp_or_consume_campaign(self):
        self.campaign()
        with patch("apps.communications.services.send_mail") as send:
            self.assertFalse(run_newsletters()["enabled"])
            send.assert_not_called()
        self.assertEqual(Campaign.objects.get().status, "scheduled")

    def test_pending_campaign_cannot_send_after_author_is_removed(self):
        self.subscriber(self.helper)
        campaign = self.campaign()
        Membership.objects.filter(user=self.coordinator).delete()
        self.assertEqual(run_newsletters()["sent"], 0)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, "draft")

    def test_preferences_require_session_csrf_and_cannot_set_another_user(self):
        self.login(self.helper)
        self.assertEqual(self.write("put", "/api/newsletter/preference", {"opted_in": True, "user": self.coordinator.pk}).status_code, 400)
        self.assertEqual(self.write("put", "/api/newsletter/preference", {"opted_in": True}).status_code, 200)
        self.assertTrue(NewsletterPreference.objects.get(user=self.helper).opted_in)

    def test_home_opt_in_requires_consent_and_uses_single_use_confirmation(self):
        _, preference = self.subscriber(self.helper, opted=False)
        token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        self.token = token
        self.assertEqual(self.write("post", "/api/newsletter/request", {"email": self.helper.email}).status_code, 400)
        response = self.write("post", "/api/newsletter/request", {"email": self.helper.email, "accepted": True})
        self.assertEqual(response.status_code, 200)
        preference.refresh_from_db()
        self.assertFalse(preference.opted_in)
        raw = mail.outbox[0].body.split("#confirmar=")[1].split()[0]
        self.assertNotEqual(preference.confirmation_hash, raw)
        self.assertEqual(self.write("post", "/api/newsletter/action", {"action": "confirm", "token": raw}).status_code, 200)
        self.assertEqual(self.write("post", "/api/newsletter/action", {"action": "confirm", "token": raw}).status_code, 400)

    def test_unknown_email_response_does_not_reveal_subscriber_identity(self):
        self.subscriber(self.helper, opted=False)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        responses = [self.write("post", "/api/newsletter/request", {"email": email, "accepted": True}).json() for email in [self.helper.email, "unknown@example.invalid"]]
        self.assertEqual(responses[0], responses[1])
        self.assertEqual(len(mail.outbox), 2)

    def test_public_unsubscribe_preserves_paid_subscription(self):
        subscription, preference = self.subscriber(self.helper)
        previous_update = preference.updated_at
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        response = self.write("post", "/api/newsletter/action", {"action": "unsubscribe", "token": str(preference.unsubscribe_token)})
        self.assertEqual(response.status_code, 200)
        preference.refresh_from_db()
        subscription.refresh_from_db()
        self.assertFalse(preference.opted_in)
        self.assertGreater(preference.updated_at, previous_update)
        self.assertEqual(subscription.status, "ACTIVE")
        self.assertGreater(subscription.paid_until, self.now)

    def test_sending_campaign_cannot_be_edited_or_deleted_and_schedule_requires_future(self):
        self.login(self.coordinator)
        campaign = self.campaign()
        campaign.status = "sending"
        campaign.save()
        self.assertEqual(self.write("patch", f"/api/communications/campaigns/{campaign.pk}", {"subject": "Alterado"}).status_code, 400)
        self.assertEqual(self.write("delete", f"/api/communications/campaigns/{campaign.pk}", {}).status_code, 400)
        self.assertEqual(self.write("post", "/api/communications/campaigns", {"subject": "Edição", "introduction": "Mensagem", "status": "scheduled"}).status_code, 400)

    def test_coordinator_can_stop_pending_delivery_after_smtp_failure(self):
        self.subscriber(self.helper)
        campaign = self.campaign()
        with patch("apps.communications.services.send_mail", side_effect=RuntimeError("smtp")):
            run_newsletters()
        self.login(self.coordinator)
        response = self.write("patch", f"/api/communications/campaigns/{campaign.pk}", {"status": "cancelled"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Delivery.objects.get().status, "skipped")
        self.assertEqual(run_newsletters()["sent"], 0)

    def test_turning_off_weekly_newsletter_cancels_pending_automatic_campaigns(self):
        self.subscriber(self.helper)
        campaign = self.campaign()
        campaign.weekly_key = "2026-W46"
        campaign.save()
        NewsletterSettings.objects.create(weekly_enabled=True, updated_by=self.coordinator)
        self.login(self.coordinator)
        response = self.write("put", "/api/communications/weekly", {"weekly_enabled": False, "weekday": 0, "hour": 9, "subject": "Nossa semana", "introduction": "Novidades"})
        self.assertEqual(response.status_code, 200)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, "cancelled")

    def test_members_event_has_public_metadata_but_private_location_and_description(self):
        event = Event.objects.create(title="Encontro especial", description="Detalhes reservados", location="Local reservado", starts_at=self.now + timedelta(days=1), is_published=True, is_members_only=True, created_by=self.coordinator)
        for endpoint in ["/api/events", "/api/mural"]:
            response = self.client.get(endpoint)
            data = response.json()["results"][0]
            self.assertEqual(data["title"], event.title)
            self.assertTrue(data["is_members_only"])
            self.assertTrue(data["is_locked"])
            self.assertIsNone(data["description"])
            self.assertIsNone(data["location"])
            self.assertNotIn("Detalhes reservados", response.content.decode())
            self.assertIn("no-store", response["Cache-Control"])
        self.login(self.helper)
        self.assertIsNone(self.client.get("/api/events").json()["results"][0]["location"])
        subscription, _ = self.subscriber(self.outsider)
        self.login(self.outsider)
        self.assertEqual(self.client.get("/api/events").json()["results"][0]["location"], "Local reservado")
        subscription.paid_until = self.now - timedelta(seconds=1)
        subscription.save()
        self.assertIsNone(self.client.get("/api/events").json()["results"][0]["description"])
        self.login(self.coordinator)
        self.assertEqual(self.client.get("/api/events").json()["results"][0]["description"], "Detalhes reservados")

    def test_coordinator_can_change_event_to_members_only_and_back_to_public(self):
        event = Event.objects.create(title="Encontro", description="Detalhes", location="Sede", starts_at=self.now + timedelta(days=1), is_published=True, created_by=self.coordinator)
        self.login(self.coordinator)
        path = f"/api/communications/events/{event.pk}"
        self.assertEqual(self.write("patch", path, {"is_members_only": True}).status_code, 200)
        self.assertEqual(self.write("patch", path, {"is_members_only": False}).status_code, 200)
        self.client.logout()
        data = self.client.get("/api/events").json()["results"][0]
        self.assertFalse(data["is_locked"])
        self.assertEqual(data["location"], "Sede")

    def test_visitor_can_confirm_receive_and_unsubscribe_without_account_or_payment(self):
        before = get_user_model().objects.count()
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        self.assertEqual(self.write("post", "/api/newsletter/request", {"email": " VISITOR@EXAMPLE.INVALID ", "accepted": True}).status_code, 200)
        preference = NewsletterPreference.objects.get(email="visitor@example.invalid")
        self.assertIsNone(preference.user_id)
        self.assertFalse(preference.opted_in)
        raw = mail.outbox[0].body.split("#confirmar=")[1].split()[0]
        self.assertEqual(self.write("post", "/api/newsletter/action", {"action": "confirm", "token": raw}).status_code, 200)
        self.assertEqual(self.write("post", "/api/newsletter/action", {"action": "confirm", "token": raw}).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), before)
        self.assertEqual(Subscription.objects.count(), 0)
        self.campaign()
        self.assertEqual(run_newsletters()["sent"], 1)
        self.assertEqual(mail.outbox[-1].to, ["visitor@example.invalid"])
        self.assertIn("Conhecer a assinatura", mail.outbox[-1].alternatives[0].content)
        self.assertEqual(self.write("post", "/api/newsletter/action", {"action": "unsubscribe", "token": str(preference.unsubscribe_token)}).status_code, 200)
        self.campaign()
        self.assertEqual(run_newsletters()["sent"], 0)

    def test_logged_in_preference_reuses_public_signup_without_losing_consent(self):
        preference = NewsletterPreference.objects.create(email=self.helper.email, opted_in=True)
        token = preference.unsubscribe_token
        self.login(self.helper)
        self.assertTrue(self.client.get("/api/newsletter/preference").json()["opted_in"])
        preference.refresh_from_db()
        self.assertEqual(preference.user, self.helper)
        self.assertEqual(preference.unsubscribe_token, token)
        self.assertEqual(NewsletterPreference.objects.count(), 1)

    def test_newsletter_does_not_leak_restricted_event_details_or_stale_public_snapshot(self):
        from .services import digest_content
        event = Event.objects.create(title="Encontro especial", description="Texto privado", location="Local privado", starts_at=self.now + timedelta(days=1), is_published=True, created_by=self.coordinator)
        campaign = Campaign(subject="Agenda", introduction="Nossas novidades", snapshot=digest_content())
        event.is_members_only = True
        event.save()
        html = render_campaign(campaign)
        self.assertIn("Encontro especial", html)
        self.assertIn("Apenas para assinantes", html)
        self.assertNotIn("Local privado", html)
        self.assertNotIn("Texto privado", html)

    def test_migration_preserves_existing_consent_and_unsubscribe_link(self):
        from importlib import import_module
        from types import SimpleNamespace
        preference = NewsletterPreference.objects.create(user=self.helper, opted_in=True, confirmation_hash="legacy-hash")
        token = preference.unsubscribe_token
        NewsletterPreference.objects.filter(pk=preference.pk).update(email="")
        migration = import_module("apps.communications.migrations.0003_event_audience_and_public_newsletter")
        migration.populate_email(SimpleNamespace(get_model=lambda *args: NewsletterPreference), None)
        preference.refresh_from_db()
        self.assertEqual(preference.email, self.helper.email)
        self.assertTrue(preference.opted_in)
        self.assertEqual(preference.unsubscribe_token, token)
        self.assertEqual(preference.confirmation_hash, "legacy-hash")
