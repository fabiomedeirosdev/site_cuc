import base64
import hashlib
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from pywebpush import WebPushException, webpush
from rest_framework.test import APIClient

from apps.billing.models import Checkout, Subscription
from apps.communications.models import Campaign, Event, NewsletterPreference
from apps.content.models import Article
from apps.editorial.models import EditorialGroup, Membership
from .models import PushDelivery, PushNotification, PushSubscription
from .services import active_user, run_push


def encoded(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


@override_settings(WEBPUSH_ENABLED=True, WEBPUSH_PUBLIC_KEY="public-test-key", WEBPUSH_PRIVATE_KEY="private-test-key", WEBPUSH_SUBJECT="mailto:test@example.invalid")
class WebPushTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.member = users.objects.create_user(username="push-member", email="push-member@example.invalid")
        cls.expired = users.objects.create_user(username="push-expired", email="push-expired@example.invalid")
        cls.founder = users.objects.create_user(username="push-founder")
        cls.founder.profile.community_role = "founder"
        cls.founder.profile.save()
        cls.developer = users.objects.create_superuser(username="push-developer", email="push-dev@example.invalid")
        cls.coordinator = users.objects.create_user(username="push-coordinator")
        cls.author = users.objects.create_user(username="push-author")
        cls.group = EditorialGroup.objects.create(name="Push grupo", slug="push-group")
        Membership.objects.create(group=cls.group, user=cls.coordinator, role="coordinator")
        Membership.objects.create(group=cls.group, user=cls.author, role="columnist")
        for user, days in [(cls.member, 2), (cls.expired, -2)]:
            Subscription.objects.create(user=user, email=user.email, provider_id=f"push-{user.pk}", checkout=Checkout.objects.create(legal_version="test"), paid_until=timezone.now() + timedelta(days=days))
        cls.key = encoded(ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))

    def setUp(self):
        cache.clear()
        self.sender = patch("apps.webpush.services.webpush").start()
        self.addCleanup(patch.stopall)

    def client_for(self, user=None):
        client = APIClient(enforce_csrf_checks=True)
        if user:
            client.force_login(user)
        client.push_csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        return client

    def data(self, suffix="visitor"):
        return {"endpoint": f"https://fcm.googleapis.com/fcm/send/{suffix}", "p256dh": self.key, "auth": encoded(b"a" * 16), "device_token": encoded(hashlib.sha256(suffix.encode()).digest())}

    def subscribe(self, user=None, suffix="visitor"):
        client = self.client_for(user)
        data = self.data(suffix)
        response = client.post("/api/push/subscription", data, format="json", HTTP_X_CSRFTOKEN=client.push_csrf)
        self.assertEqual(response.status_code, 200, response.content)
        return client, PushSubscription.objects.get(endpoint=data["endpoint"])

    def article(self, **kwargs):
        defaults = {"author": self.author, "group": self.group, "title": "Título restrito que não deve vazar", "body": "Texto privado", "status": "published", "published_at": timezone.now()}
        with self.captureOnCommitCallbacks(execute=True):
            return Article.objects.create(**{**defaults, **kwargs})

    def event(self, **kwargs):
        defaults = {"title": "Encontro", "description": "Descrição privada", "location": "Local privado", "starts_at": timezone.now() + timedelta(days=2), "created_by": self.coordinator, "is_published": True}
        with self.captureOnCommitCallbacks(execute=True):
            return Event.objects.create(**{**defaults, **kwargs})

    def test_anonymous_registration_requires_csrf_and_does_not_enroll_newsletter(self):
        client = self.client_for()
        self.assertEqual(client.post("/api/push/subscription", self.data(), format="json").status_code, 403)
        _, subscription = self.subscribe()
        self.assertIsNone(subscription.user_id)
        self.assertEqual(subscription.session_key, "")
        self.assertFalse(NewsletterPreference.objects.exists())
        self.assertFalse(Campaign.objects.exists())

    def test_duplicate_registration_and_device_ownership(self):
        client, subscription = self.subscribe()
        self.assertEqual(client.post("/api/push/subscription", self.data(), format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 1)
        data = {**self.data(), "device_token": "x" * 43}
        self.assertEqual(client.post("/api/push/subscription", data, format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 403)
        self.assertEqual(client.delete("/api/push/subscription", data, format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 403)
        self.assertEqual(PushSubscription.objects.get(pk=subscription.pk).device_hash, hashlib.sha256(self.data()["device_token"].encode()).hexdigest())

    def test_private_networks_foreign_hosts_ports_and_invalid_keys_are_rejected(self):
        client = self.client_for()
        for endpoint in ["http://fcm.googleapis.com/send/1", "https://127.0.0.1/x", "https://example.com/x", "https://fcm.googleapis.com.evil.invalid/x", "https://fcm.googleapis.com:8443/x", "https://user@fcm.googleapis.com/x"]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(client.post("/api/push/subscription", {**self.data(), "endpoint": endpoint}, format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 400)
        for field, value in [("auth", "bad"), ("p256dh", encoded(b"\x04" + b"0" * 64)), ("device_token", "short")]:
            self.assertEqual(client.post("/api/push/subscription", {**self.data(), field: value}, format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_configuration_hides_private_key_and_disabled_signup(self):
        client = self.client_for()
        data = client.get("/api/push/config").json()
        self.assertEqual(set(data), {"enabled", "public_key"})
        with override_settings(WEBPUSH_ENABLED=False):
            self.assertEqual(client.get("/api/push/config").json(), {"enabled": False, "public_key": None})
            self.assertEqual(client.post("/api/push/subscription", self.data(), format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 503)
            self.article()
            self.assertFalse(PushNotification.objects.exists())

    def test_registration_endpoint_is_throttled(self):
        client = self.client_for()
        for _ in range(30):
            client.get("/api/push/config")
        self.assertEqual(client.get("/api/push/config").status_code, 429)

    def test_public_articles_reach_visitors_and_all_roles_once(self):
        for index, user in enumerate([None, self.member, self.expired, self.founder, self.developer, self.coordinator, self.author]):
            self.subscribe(user, str(index))
        article = self.article()
        self.assertEqual(run_push()["sent"], 7)
        self.assertEqual(run_push()["sent"], 0)
        with self.captureOnCommitCallbacks(execute=True):
            article.title = "Edição posterior"
            article.save()
            article.status = "draft"
            article.save()
            article.status = "published"
            article.save()
        self.assertEqual(PushNotification.objects.count(), 1)
        self.assertEqual(run_push()["sent"], 0)
        message = json.loads(self.sender.call_args.kwargs["data"])
        self.assertNotIn("Título restrito", str(message))
        self.assertNotIn("Texto privado", str(message))
        self.assertEqual(message["url"], f"/conteudos/{article.pk}")

    def test_drafts_only_queue_on_first_publication(self):
        self.subscribe()
        article = self.article(status="draft")
        self.event(is_published=False)
        self.assertFalse(PushNotification.objects.exists())
        with self.captureOnCommitCallbacks(execute=True):
            article.status = "published"
            article.save()
        self.assertEqual(run_push()["sent"], 1)

    def test_articles_from_multiple_groups_and_new_events(self):
        self.subscribe()
        other = EditorialGroup.objects.create(name="Outro", slug="push-other")
        Membership.objects.create(group=other, user=self.author, role="columnist")
        self.article()
        self.article(group=other)
        event = self.event()
        self.assertEqual(run_push()["sent"], 3)
        self.assertIn(f"/agenda.html#evento-{event.pk}", [json.loads(call.kwargs["data"])["url"] for call in self.sender.call_args_list])
        with self.captureOnCommitCallbacks(execute=True):
            event.title = "Evento revisado"
            event.save()
        self.assertEqual(run_push()["sent"], 0)

    def test_exclusive_article_uses_existing_read_permissions(self):
        for index, user in enumerate([None, self.member, self.expired, self.founder, self.developer, self.coordinator, self.author]):
            self.subscribe(user, str(index))
        self.article(audience="members")
        self.assertEqual(run_push()["sent"], 3)  # paid member + founder + developer
        recipients = {call.kwargs["subscription_info"]["endpoint"] for call in self.sender.call_args_list}
        self.assertEqual(recipients, {self.data(str(i))["endpoint"] for i in [1, 3, 4]})

    def test_exclusive_event_allows_existing_agenda_managers(self):
        for index, user in enumerate([None, self.member, self.expired, self.founder, self.developer, self.coordinator, self.author]):
            self.subscribe(user, str(index))
        self.event(is_members_only=True)
        self.assertEqual(run_push()["sent"], 4)

    def test_logout_detaches_and_prevents_queued_exclusive_delivery(self):
        client, subscription = self.subscribe(self.member)
        article = self.article(audience="members")
        notification = PushNotification.objects.get(object_id=article.pk)
        PushDelivery.objects.create(notification=notification, subscription=subscription)
        response = client.post("/api/auth/logout", {}, format="json", HTTP_X_CSRFTOKEN=client.push_csrf)
        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertIsNone(subscription.user_id)
        self.assertEqual(subscription.session_key, "")
        self.assertEqual(run_push()["skipped"], 1)
        self.sender.assert_not_called()
        self.article()
        self.assertEqual(run_push()["sent"], 1)  # visitor opt-in remains public-only

    def test_expiration_safety_hold_and_session_revocation_are_rechecked(self):
        _, subscription = self.subscribe(self.member)
        self.article(audience="members")
        Subscription.objects.filter(user=self.member).update(safety_hold=True)
        self.assertEqual(run_push()["sent"], 0)
        Subscription.objects.filter(user=self.member).update(safety_hold=False)
        self.article(audience="members")
        Session.objects.filter(session_key=subscription.session_key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(run_push()["sent"], 0)
        self.assertIsNone(active_user(subscription))

    def test_password_change_invalidates_old_session(self):
        _, subscription = self.subscribe(self.member)
        self.member.set_password("Changed-Push!Test-19")
        self.member.save()
        subscription.refresh_from_db()
        self.assertIsNone(active_user(subscription))

    def test_account_switch_rebinds_only_with_device_proof(self):
        client, subscription = self.subscribe(self.member)
        client.force_login(self.expired)
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        self.assertEqual(client.post("/api/push/subscription", self.data(), format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.user_id, self.expired.pk)
        self.article(audience="members")
        self.assertEqual(run_push()["sent"], 0)

    def test_unsubscribe_is_idempotent_and_removes_queued_deliveries(self):
        client, subscription = self.subscribe()
        self.article()
        notification = PushNotification.objects.get()
        PushDelivery.objects.create(notification=notification, subscription=subscription)
        data = {key: value for key, value in self.data().items() if key in {"endpoint", "device_token"}}
        for _ in range(2):
            self.assertEqual(client.delete("/api/push/subscription", data, format="json", HTTP_X_CSRFTOKEN=client.push_csrf).status_code, 204)
        self.assertFalse(PushDelivery.objects.exists())
        self.assertEqual(run_push()["sent"], 0)

    def test_withdrawn_content_and_cancelled_events_are_not_sent(self):
        self.subscribe()
        article = self.article()
        event = self.event()
        Article.objects.filter(pk=article.pk).update(status="draft")
        Event.objects.filter(pk=event.pk).update(is_cancelled=True)
        self.assertEqual(run_push()["sent"], 0)
        self.sender.assert_not_called()

    def test_lost_author_permission_suppresses_delivery(self):
        self.subscribe()
        self.article()
        Membership.objects.filter(user=self.author).delete()
        self.assertEqual(run_push()["sent"], 0)

    def test_invalid_provider_subscription_is_removed(self):
        self.subscribe()
        self.article()
        self.sender.side_effect = WebPushException("gone", response=Mock(status_code=410))
        self.assertEqual(run_push()["invalid"], 1)
        self.assertFalse(PushSubscription.objects.exists())

    def test_transient_errors_retry_and_permanent_errors_stop(self):
        self.subscribe()
        self.article()
        self.sender.side_effect = WebPushException("unavailable", response=Mock(status_code=503))
        self.assertEqual(run_push()["retried"], 1)
        delivery = PushDelivery.objects.get()
        self.assertEqual(delivery.attempts, 1)
        self.assertGreater(delivery.next_attempt_at, timezone.now())
        self.assertEqual(run_push()["retried"], 0)
        PushDelivery.objects.update(next_attempt_at=timezone.now())
        self.sender.side_effect = WebPushException("denied", response=Mock(status_code=401))
        self.assertEqual(run_push()["failed"], 1)
        self.assertEqual(PushDelivery.objects.get().last_error, "http_401")

    def test_small_batches_and_new_devices_do_not_receive_old_notifications(self):
        self.subscribe(suffix="one")
        self.subscribe(suffix="two")
        self.article()
        self.subscribe(suffix="new-after-publication")
        self.assertEqual(run_push(batch_size=1)["sent"], 1)
        self.assertEqual(run_push(batch_size=1)["sent"], 1)
        self.assertEqual(run_push(batch_size=1)["sent"], 0)

    def test_stale_queue_does_not_send_old_news(self):
        self.subscribe()
        self.article()
        PushNotification.objects.update(created_at=timezone.now() - timedelta(days=2))
        self.assertEqual(run_push()["sent"], 0)

    def test_expiration_after_queueing_prevents_delivery(self):
        _, subscription = self.subscribe(self.member)
        self.article(audience="members")
        PushDelivery.objects.create(notification=PushNotification.objects.get(), subscription=subscription)
        Subscription.objects.filter(user=self.member).update(paid_until=timezone.now() - timedelta(seconds=1))
        self.assertEqual(run_push()["skipped"], 1)
        self.sender.assert_not_called()

    def test_rolled_back_publication_does_not_queue_or_send(self):
        self.subscribe()
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Article.objects.create(author=self.author, group=self.group, title="Rollback", status="published")
                    raise ValueError("rollback")
            except ValueError:
                pass
        self.assertFalse(PushNotification.objects.exists())
        self.sender.assert_not_called()

    def test_ongoing_events_follow_the_existing_agenda_window(self):
        self.subscribe()
        self.event(starts_at=timezone.now() - timedelta(hours=1), ends_at=timezone.now() + timedelta(hours=1))
        self.event(starts_at=timezone.now() - timedelta(hours=2), ends_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(run_push()["sent"], 1)

    def test_partial_save_does_not_queue_an_unpersisted_publication(self):
        self.subscribe()
        article = self.article(status="draft")
        with self.captureOnCommitCallbacks(execute=True):
            article.status = "published"
            article.title = "Ainda é rascunho no banco"
            article.save(update_fields=["title"])
        self.assertFalse(PushNotification.objects.exists())
        with self.captureOnCommitCallbacks(execute=True):
            article.save(update_fields=["status"])
        self.assertEqual(run_push()["sent"], 1)

    def test_previously_cancelled_event_queues_only_when_first_available(self):
        self.subscribe()
        event = self.event(is_cancelled=True)
        self.assertFalse(PushNotification.objects.exists())
        with self.captureOnCommitCallbacks(execute=True):
            event.is_cancelled = False
            event.save(update_fields=["is_cancelled"])
        self.assertEqual(run_push()["sent"], 1)

    def test_real_library_encrypts_and_signs_without_network(self):
        private = ec.generate_private_key(ec.SECP256R1())
        encoded_private = base64.b64encode(private.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).decode()
        transport = Mock()
        transport.post.return_value = Mock(status_code=201)
        webpush(subscription_info={"endpoint": self.data()["endpoint"], "keys": {"p256dh": self.key, "auth": self.data()["auth"]}}, data="Mensagem de teste", vapid_private_key=encoded_private, vapid_claims={"sub": "mailto:test@example.invalid"}, requests_session=transport, timeout=5)
        request = transport.post.call_args.kwargs
        self.assertNotIn(b"Mensagem de teste", request["data"])
        self.assertIn("authorization", {key.lower() for key in request["headers"]})
