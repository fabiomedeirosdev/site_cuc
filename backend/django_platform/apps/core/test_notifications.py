from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.billing.models import Checkout, ConsumerRequest, Subscription
from apps.communications.models import Event, Notice
from apps.content.models import Article
from apps.editorial.models import EditorialGroup, Membership
from .inbox import import_message, synchronize_inbox, webmail_url
from .models import InboxMailbox, IncomingMessage


class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username="notification-admin", email="admin@example.invalid", is_superuser=True)
        cls.founder = User.objects.create_user(username="notification-founder", email="founder@example.invalid")
        cls.founder.profile.community_role = "founder"
        cls.founder.profile.save()
        cls.helper = User.objects.create_user(username="notification-helper", email="helper@example.invalid")
        cls.coordinator = User.objects.create_user(username="notification-coord", email="coord@example.invalid")
        cls.reader = User.objects.create_user(username="notification-reader", email="reader@example.invalid")
        cls.other = User.objects.create_user(username="notification-other", email="other@example.invalid", is_staff=True)
        cls.group = EditorialGroup.objects.create(name="Grupo notificação", slug="notifications-test")
        Membership.objects.create(group=cls.group, user=cls.helper, role="columnist")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        cls.public = Article.objects.create(group=cls.group, author=cls.helper, title="Notícia pública", body="Texto", status="published")
        cls.exclusive = Article.objects.create(group=cls.group, author=cls.helper, title="Título reservado", body="Segredo", status="published", audience="members")
        cls.draft = Article.objects.create(group=cls.group, author=cls.helper, title="Rascunho reservado", body="Rascunho")
        cls.notice = Notice.objects.create(title="Aviso público", body="Corpo", is_published=True, created_by=cls.admin)
        cls.private_notice = Notice.objects.create(title="Aviso exclusivo", body="Corpo secreto", is_members_only=True, is_published=True, created_by=cls.admin)
        cls.event = Event.objects.create(title="Encontro", description="Oração", location="Sede", starts_at=timezone.now()+timedelta(days=3), is_published=True, created_by=cls.admin)
        cls.email = IncomingMessage.objects.create(source_key="fixture-1", sender="outside@example.invalid", subject="Pedido externo", body="Mensagem externa")
        cls.checkout = Checkout.objects.create()
        cls.subscription = Subscription.objects.create(checkout=cls.checkout, provider_id="notification-subscription", email=cls.reader.email, user=cls.reader, paid_until=timezone.now()+timedelta(days=4))
        ConsumerRequest.objects.create(subscription=cls.subscription, kind="privacy", message="Privacidade")

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def post(self, data, csrf=True):
        return self.client.post("/api/notifications", data, format="json", **({"HTTP_X_CSRFTOKEN": self.token} if csrf else {}))

    def test_anonymous_notifications_and_inbox_are_denied(self):
        for path in ["/api/notifications", "/api/inbox", f"/api/inbox/{self.email.pk}"]:
            self.assertEqual(self.client.get(path).status_code, 403)

    def test_active_subscriber_sees_updates_but_no_incoming_or_private_requests(self):
        self.login(self.reader)
        response = self.client.get("/api/notifications").json()
        self.assertIn(self.exclusive.title, str(response))
        self.assertNotIn(self.draft.title, str(response))
        self.assertNotIn(self.email.subject, str(response))
        self.assertEqual(response["pending_count"], 0)
        self.assertEqual(self.client.get("/api/inbox").status_code, 403)

    def test_expired_and_suspended_access_do_not_leak_exclusive_titles(self):
        for changes in [{"paid_until": timezone.now()-timedelta(days=1)}, {"paid_until": timezone.now()+timedelta(days=1), "safety_hold": True}]:
            Subscription.objects.filter(pk=self.subscription.pk).update(**changes)
            self.login(self.reader)
            response = self.client.get("/api/notifications").json()
            self.assertIn(self.public.title, str(response))
            self.assertNotIn(self.exclusive.title, str(response))
            self.assertNotIn(self.private_notice.title, str(response))

    def test_team_gets_external_messages_without_billing_request_privileges(self):
        for person in [self.helper, self.coordinator, self.founder, self.admin]:
            self.login(person)
            response = self.client.get("/api/notifications").json()
            self.assertTrue(any(row["kind"] == "email" for row in response["pending"]))
            self.assertEqual(self.client.get(f"/api/inbox/{self.email.pk}").json()["body"], self.email.body)
            requests = [row for row in response["pending"] if row["kind"] == "request"]
            self.assertEqual(bool(requests), person in [self.admin, self.founder])
        self.login(self.other)
        self.assertEqual(self.client.get("/api/inbox").status_code, 403)

    def test_general_facilitator_and_revoked_group_membership(self):
        Membership.objects.filter(user=self.helper).delete()
        self.login(self.helper)
        self.assertEqual(self.client.get("/api/inbox").status_code, 403)
        self.helper.profile.community_role = "columnist"
        self.helper.profile.save()
        self.assertEqual(self.client.get("/api/inbox").status_code, 200)

    def test_read_is_private_monotonic_and_does_not_clear_pending_emails(self):
        self.login(self.helper)
        response = self.client.get("/api/notifications").json()
        self.assertGreater(response["unread_count"], 0)
        self.assertEqual(self.post({"seen_until": response["as_of"]}).status_code, 200)
        after = self.client.get("/api/notifications").json()
        self.assertEqual(after["unread_count"], 0)
        self.assertEqual(after["pending_count"], 1)
        self.post({"seen_until": (timezone.now()-timedelta(days=20)).isoformat()})
        self.assertEqual(self.client.get("/api/notifications").json()["unread_count"], 0)
        self.login(self.reader)
        self.assertGreater(self.client.get("/api/notifications").json()["unread_count"], 0)

    def test_csrf_future_timestamp_and_privilege_fields_are_rejected(self):
        self.login(self.reader)
        self.assertEqual(self.post({"seen_until": timezone.now().isoformat()}, csrf=False).status_code, 403)
        self.assertEqual(self.post({"seen_until": (timezone.now()+timedelta(days=1)).isoformat()}).status_code, 400)
        self.assertEqual(self.post({"seen_until": timezone.now().isoformat(), "user": self.admin.pk}).status_code, 400)

    def test_pending_response_and_reopen_are_reflected_in_notifications(self):
        self.login(self.helper)
        path = f"/api/inbox/{self.email.pk}"
        self.assertEqual(self.client.patch(path, {"responded": True}, format="json").status_code, 403)
        response = self.client.patch(path, {"responded": True}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/notifications").json()["pending_count"], 0)
        self.assertEqual(self.client.get("/api/inbox").json()["count"], 0)
        self.assertEqual(self.client.get("/api/inbox?status=all").json()["count"], 1)
        self.client.patch(path, {"responded": False}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(self.client.get("/api/notifications").json()["pending_count"], 1)

    def test_hidden_inactive_old_or_draft_publications_do_not_notify(self):
        Article.objects.filter(pk=self.public.pk).update(updated_at=timezone.now()-timedelta(days=31))
        self.login(self.reader)
        response = self.client.get("/api/notifications").json()
        self.assertNotIn(self.public.title, str(response))
        self.group.is_active = False
        self.group.save()
        response = self.client.get("/api/notifications").json()
        self.assertFalse(any(row["kind"] == "article" for row in response["updates"]))


class InboxImportTests(TestCase):
    def test_import_decodes_text_and_deduplicates(self):
        raw = b'From: Pessoa <person@example.invalid>\r\nSubject: =?utf-8?b?T2zDoQ==?=\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPreciso de ajuda.'
        message, created = import_message(raw, "source-1")
        self.assertTrue(created)
        self.assertEqual(message.sender, "person@example.invalid")
        self.assertEqual(message.subject, "Olá")
        self.assertIn("Preciso de ajuda", message.body)
        self.assertFalse(import_message(raw, "source-1")[1])
        self.assertEqual(IncomingMessage.objects.count(), 1)

    def test_html_and_attachments_are_not_rendered_as_message_body(self):
        message, _ = import_message(b'From: bad\r\nSubject: HTML\r\nContent-Type: text/html\r\n\r\n<script>alert(1)</script><img src="https://outside.invalid/track">', "html")
        self.assertNotIn("<script>", message.body)
        self.assertNotIn("outside.invalid", message.body)
        self.assertEqual(message.sender, "")

    @override_settings(INBOX_ENABLED=False)
    def test_disabled_integration_never_connects(self):
        with patch("apps.core.inbox.imaplib.IMAP4_SSL") as client:
            with self.assertRaises(CommandError):
                call_command("sync_inbox", stdout=StringIO(), stderr=StringIO())
            client.assert_not_called()

    @override_settings(INBOX_ENABLED=True, INBOX_IMAP_HOST="mail.example.invalid", INBOX_IMAP_USER="contact@example.invalid", INBOX_IMAP_PASSWORD="test-only", INBOX_IMAP_FOLDER="INBOX", INBOX_IMAP_PORT=993)
    def test_imap_cursor_reads_without_marking_mail_seen_and_ignores_repeated_uid(self):
        mail = MagicMock()
        mail.__enter__.return_value = mail
        mail.select.return_value = ("OK", [b"1"])
        mail.response.return_value = ("UIDVALIDITY", [b"17"])
        def uid(command, *args):
            if command == "search":
                return "OK", [b"7"]
            if args[1] == "(RFC822.SIZE)":
                return "OK", [b"7 (RFC822.SIZE 99)"]
            self.assertEqual(args[1], "(BODY.PEEK[])")
            return "OK", [(b"7 (BODY[] {99}", b"From: outside@example.invalid\r\nSubject: Help\r\n\r\nMessage")]
        mail.uid.side_effect = uid
        with patch("apps.core.inbox.imaplib.IMAP4_SSL", return_value=mail):
            self.assertEqual(synchronize_inbox(), 1)
            self.assertEqual(synchronize_inbox(), 0)
        mail.select.assert_called_with("INBOX", readonly=True)
        self.assertEqual(InboxMailbox.objects.get().last_uid, 7)
        self.assertEqual(IncomingMessage.objects.count(), 1)

    def test_webmail_requires_https_without_embedded_credentials(self):
        for value in ["javascript:alert(1)", "http://mail.example.invalid", "https://user:secret@mail.example.invalid"]:
            with override_settings(INBOX_WEBMAIL_URL=value):
                self.assertEqual(webmail_url(), "")
