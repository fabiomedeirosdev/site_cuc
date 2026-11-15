from dataclasses import replace
from datetime import timedelta
import re
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError as ApiValidationError

from apps.content.models import Article
from apps.editorial.models import EditorialGroup, Membership
from .access import account_subscription, has_access
from .models import Checkout, ConsumerRequest, EmailJob, Invitation, LegalAcceptance, PaidPeriod, Subscription
from .provider import PagBank, ProviderUnavailable, Snapshot, provider_datetime, ready
from .services import complete_invitation, deliver_email, synchronize


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", PUBLIC_FRONTEND_URL="https://example.invalid", MERCHANT_CONTACT_EMAIL="support@example.invalid")
class BillingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="paid-reader", email="reader@example.invalid", password="ReaderTest!81-Password")
        cls.other = get_user_model().objects.create_user(username="other-reader", email="other@example.invalid", password="OtherTest!81-Password")
        cls.checkout = Checkout.objects.create(plan_id="PLAN_" + str(uuid4()), legal_version=settings.BILLING_LEGAL_VERSION)
        cls.identifier = "SUBS_" + str(uuid4())

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.client = APIClient(enforce_csrf_checks=True)
        self.now = timezone.now()
        self.snapshot = Snapshot(self.identifier, self.checkout.plan_id, "paid@example.invalid", "ACTIVE", self.now, self.now - timedelta(days=15), self.now + timedelta(days=15), 4800, "BRL")

    def sync(self, snapshot=None, send=False):
        with patch.object(PagBank, "subscription", return_value=snapshot or self.snapshot), self.captureOnCommitCallbacks(execute=send):
            return synchronize(self.identifier)

    def session(self, user):
        self.client.force_login(user)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]

    def post(self, path, data=None):
        return self.client.post(path, data or {}, format="json", HTTP_X_CSRFTOKEN=self.token)

    def invitation(self, email="new@example.invalid"):
        subscription = self.sync(replace(self.snapshot, email=email), send=True)
        token = re.search(r"#convite=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
        return subscription, token

    def test_duplicate_verified_payments_create_one_period_and_one_email(self):
        subscription = self.sync(send=True)
        self.sync(send=True)
        self.sync(send=True)
        self.assertEqual(PaidPeriod.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(subscription.paid_until, self.snapshot.paid_until)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_cancel_preserves_fifteen_or_one_day_and_expires_at_exact_boundary(self):
        for days in [15, 1]:
            with self.subTest(days=days):
                end = self.now + timedelta(days=days)
                snapshot = replace(self.snapshot, paid_until=end)
                subscription = self.sync(snapshot)
                subscription.user = self.user
                subscription.save()
                self.sync(replace(snapshot, status="CANCELED", paid_until=None, updated_at=self.now + timedelta(seconds=1)))
                subscription.refresh_from_db()
                self.assertEqual(subscription.paid_until, end)
                with patch("django.utils.timezone.now", return_value=end - timedelta(microseconds=1)):
                    self.assertTrue(has_access(self.user))
                    self.assertEqual(account_subscription(self.user)["status"], "canceled_paid")
                with patch("django.utils.timezone.now", return_value=end):
                    self.assertFalse(has_access(self.user))
                PaidPeriod.objects.all().delete()
                Subscription.objects.all().delete()

    def test_late_failed_suspended_or_trial_state_does_not_grant_an_extra_month(self):
        subscription = self.sync()
        for index, status in enumerate(["OVERDUE", "SUSPENDED", "PENDING_ACTION", "TRIAL"]):
            self.sync(replace(self.snapshot, status=status, paid_until=None, updated_at=self.now + timedelta(seconds=index + 1)))
            subscription.refresh_from_db()
            self.assertEqual(subscription.paid_until, self.snapshot.paid_until)
        self.assertEqual(PaidPeriod.objects.count(), 1)

    def test_renewal_extends_only_to_new_confirmed_bank_date(self):
        subscription = self.sync(replace(self.snapshot, paid_until=self.now + timedelta(days=1)))
        self.sync(replace(self.snapshot, paid_until=self.now + timedelta(days=31), updated_at=self.now + timedelta(seconds=1)))
        subscription.refresh_from_db()
        self.assertEqual(subscription.paid_until, self.now + timedelta(days=31))
        self.assertEqual(PaidPeriod.objects.count(), 2)

    def test_out_of_order_snapshot_and_reactivation_cannot_restore_canceled_subscription(self):
        self.sync()
        self.sync(replace(self.snapshot, status="CANCELED", paid_until=None, updated_at=self.now + timedelta(seconds=5)))
        subscription = self.sync(self.snapshot)
        self.assertEqual(subscription.status, "CANCELED")
        with self.assertRaises(ProviderUnavailable):
            self.sync(replace(self.snapshot, updated_at=self.now + timedelta(seconds=10)))

    def test_unrecognized_plan_wrong_amount_or_currency_cannot_grant_access(self):
        self.assertIsNone(self.sync(replace(self.snapshot, plan_id="PLAN_unknown")))
        for snapshot in [replace(self.snapshot, amount=1), replace(self.snapshot, currency="USD"), replace(self.snapshot, paid_until=self.now + timedelta(days=365))]:
            with self.assertRaises(ProviderUnavailable):
                self.sync(snapshot)
        self.assertEqual(Subscription.objects.count(), 0)

    @override_settings(BILLING_ENABLED=True)
    def test_webhook_uses_authenticated_query_not_supplied_status_or_dates(self):
        with patch.object(PagBank, "subscription", return_value=replace(self.snapshot, status="PENDING", paid_until=None)):
            response = self.client.post("/api/billing/webhooks/pagbank", {"event": "subscription.activated", "resource": {"id": self.identifier, "status": "ACTIVE", "paid_until": "2999-01-01", "amount": 1}}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Subscription.objects.get().paid_until)
        self.assertEqual(EmailJob.objects.count(), 0)

    @override_settings(BILLING_ENABLED=True)
    def test_bank_failure_rejects_webhook_without_granting_access(self):
        with patch.object(PagBank, "subscription", side_effect=ProviderUnavailable("offline")):
            response = self.client.post("/api/billing/webhooks/pagbank", {"event": "subscription.recurrence", "resource": {"id": self.identifier}}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_invitation_is_hashed_single_use_and_creates_only_subscriber(self):
        subscription, token = self.invitation()
        invitation = Invitation.objects.get(subscription=subscription)
        self.assertNotEqual(invitation.token_hash, token)
        self.assertNotIn(token, invitation.token_hash)
        user = complete_invitation(token, "Pessoa assinante", "NewAccountTest!81-Password")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("NewAccountTest!81-Password"))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Assinantes"])
        self.assertTrue(has_access(user))
        self.assertEqual(LegalAcceptance.objects.filter(user=user).count(), 1)
        with self.assertRaises(ApiValidationError):
            complete_invitation(token, "Outro nome", "OtherAccountTest!81-Password")

    def test_existing_account_requires_owner_login_and_never_resets_password(self):
        subscription, token = self.invitation(self.user.email)
        for user in [None, self.other]:
            with self.assertRaises(ApiValidationError):
                complete_invitation(token, "Outra pessoa", "UnsafePassword!81", user=user)
        complete_invitation(token, "", "", user=self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ReaderTest!81-Password"))
        self.assertTrue(has_access(self.user))

    def test_expired_token_expired_paid_period_and_safety_hold_block_registration(self):
        subscription, token = self.invitation()
        Invitation.objects.filter(subscription=subscription).update(expires_at=self.now - timedelta(seconds=1))
        with self.assertRaises(ApiValidationError):
            complete_invitation(token, "Pessoa", "NewAccountTest!81-Password")
        Invitation.objects.filter(subscription=subscription).update(expires_at=self.now + timedelta(days=1))
        subscription.paid_until = self.now - timedelta(seconds=1)
        subscription.save()
        with self.assertRaises(ApiValidationError):
            complete_invitation(token, "Pessoa", "NewAccountTest!81-Password")

    def test_email_failure_keeps_durable_retry_and_does_not_undo_payment(self):
        with patch("apps.billing.services.send_mail", side_effect=RuntimeError("smtp offline")):
            subscription = self.sync(send=True)
        job = EmailJob.objects.get()
        self.assertIsNone(job.sent_at)
        self.assertEqual(job.last_error, "email_unavailable")
        self.assertIsNotNone(subscription.paid_until)
        deliver_email(job.pk)
        job.refresh_from_db()
        self.assertIsNotNone(job.sent_at)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(BILLING_ENABLED=True)
    def test_owner_cancellation_is_idempotent_and_preserves_access(self):
        subscription = self.sync()
        subscription.user = self.user
        subscription.save()
        self.session(self.other)
        path = f"/api/billing/subscriptions/{subscription.pk}/cancel"
        self.assertEqual(self.post(path).status_code, 404)
        self.session(self.user)
        with patch.object(PagBank, "cancel", return_value={}) as cancel:
            self.assertEqual(self.post(path).status_code, 200)
            self.assertEqual(self.post(path).status_code, 200)
            self.assertEqual(cancel.call_count, 1)
        self.assertTrue(has_access(self.user))

    @override_settings(BILLING_ENABLED=True)
    def test_failed_cancellation_is_saved_for_retry_and_not_reported_as_success(self):
        subscription = self.sync()
        subscription.user = self.user
        subscription.save()
        self.session(self.user)
        with patch.object(PagBank, "cancel", side_effect=ProviderUnavailable("offline")):
            response = self.post(f"/api/billing/subscriptions/{subscription.pk}/cancel")
        self.assertEqual(response.status_code, 503)
        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.cancel_requested_at)
        self.assertEqual(subscription.status, "ACTIVE")
        self.assertTrue(has_access(self.user))

    def test_exclusive_body_and_video_are_removed_after_paid_boundary_even_with_session(self):
        facilitator = self.other
        group = EditorialGroup.objects.create(name="Teste pago", slug="teste-pago", description="Teste")
        Membership.objects.create(group=group, user=facilitator, role="columnist")
        article = Article.objects.create(author=facilitator, group=group, title="Conteúdo pago", body="Texto protegido", audience="members", status="published", video_url="https://youtu.be/abcdefghijk")
        subscription = self.sync()
        subscription.user = self.user
        subscription.paid_until = self.now + timedelta(minutes=1)
        subscription.save()
        self.session(self.user)
        response = self.client.get(f"/api/articles/{article.pk}")
        self.assertEqual(response.json()["body"], "Texto protegido")
        self.assertIn("youtube-nocookie.com", response.json()["video_embed_url"])
        self.assertIn("no-store", response["Cache-Control"])
        with patch("django.utils.timezone.now", return_value=subscription.paid_until):
            self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
            data = self.client.get(f"/api/articles/{article.pk}").json()
            self.assertIsNone(data["body"])
            self.assertIsNone(data["video_embed_url"])
            self.assertTrue(data["is_locked"])

    def test_public_registration_needs_valid_token_acceptance_and_csrf(self):
        _, token = self.invitation()
        data = {"token": token, "name": "Pessoa assinante", "password": "NewAccountTest!81-Password", "accepted": True, "legal_version": settings.BILLING_LEGAL_VERSION}
        self.assertEqual(self.client.post("/api/billing/invitation/complete", data, format="json").status_code, 403)
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        self.assertEqual(self.post("/api/billing/invitation/complete", {**data, "is_staff": True}).status_code, 400)
        self.assertEqual(self.post("/api/billing/invitation/complete", {**data, "accepted": False}).status_code, 400)
        self.assertEqual(self.post("/api/billing/invitation/complete", data).status_code, 200)
        self.assertTrue(self.client.get("/api/auth/me").json()["exclusive_content_access"])

    def test_consumer_request_is_private_and_deduplicated(self):
        subscription = self.sync()
        subscription.user = self.user
        subscription.save()
        path = f"/api/billing/subscriptions/{subscription.pk}/requests"
        self.session(self.other)
        self.assertEqual(self.post(path, {"kind": "withdrawal"}).status_code, 404)
        self.session(self.user)
        first = self.post(path, {"kind": "withdrawal", "message": "Solicito arrependimento"})
        second = self.post(path, {"kind": "withdrawal"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["protocol"], second.json()["protocol"])
        self.assertEqual(ConsumerRequest.objects.count(), 1)

    def test_pending_subscription_does_not_hide_valid_paid_period_of_same_account(self):
        subscription = self.sync()
        subscription.user = self.user
        subscription.save()
        Subscription.objects.create(checkout=self.checkout, provider_id="SUBS_" + str(uuid4()), email=self.user.email, user=self.user)
        data = account_subscription(self.user)
        self.assertTrue(data["has_access"])
        self.assertEqual(data["access_until"], self.snapshot.paid_until)

    def test_date_only_bank_cycle_uses_brasilia_timezone(self):
        parsed = provider_datetime("2026-11-12")
        self.assertEqual(parsed.isoformat(), "2026-11-12T00:00:00-03:00")

    def test_disabled_checkout_cannot_create_or_charge_anything(self):
        self.token = self.client.get("/api/auth/csrf").json()["csrf_token"]
        with patch.object(PagBank, "create_checkout") as create:
            response = self.post("/api/billing/checkout", {"accepted": True, "legal_version": settings.BILLING_LEGAL_VERSION})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Checkout.objects.count(), 1)
        create.assert_not_called()

    def test_malformed_bank_dates_and_customer_email_are_rejected(self):
        for value in [None, "2026-99-99", "2026-11-12T99:99:99Z", "2026-11-12T10:00:00"]:
            with self.subTest(value=value), self.assertRaises(ProviderUnavailable):
                provider_datetime(value)
        data = {"id": self.identifier, "plan": {}, "customer": {"email": None}, "amount": {}}
        with patch.object(PagBank, "request", return_value=data), self.assertRaises(ProviderUnavailable):
            PagBank().subscription(self.identifier)

    def test_monthly_checkout_uses_server_price_and_recurring_plan(self):
        payload = {"id": "CHEC_test", "recurrence_plan": {"id": self.checkout.plan_id}, "links": [{"rel": "PAY", "href": "https://qa.pagamento.pagseguro.uol.com.br/pagamento?code=TEST"}]}
        with patch.object(PagBank, "request", return_value=payload) as request:
            result = PagBank().create_checkout(self.checkout)
        self.assertEqual(result["plan_id"], self.checkout.plan_id)
        body = request.call_args.args[4]
        self.assertEqual(body["items"][0]["unit_amount"], 4800)
        self.assertEqual(body["recurrence_plan"]["interval"], {"unit": "MONTH", "length": 1})
        self.assertNotIn("billing_cycles", body["recurrence_plan"])
        self.assertEqual(request.call_args.kwargs["key"], self.checkout.pk)

    def test_checkout_rejects_unrecognized_payment_host(self):
        payload = {"id": "CHEC_test", "recurrence_plan": {"id": self.checkout.plan_id}, "links": [{"rel": "PAY", "href": "https://fake.example.invalid/pagamento"}]}
        with patch.object(PagBank, "request", return_value=payload), self.assertRaises(ProviderUnavailable):
            PagBank().create_checkout(self.checkout)

    @override_settings(BILLING_ENABLED=True, PAGBANK_CHECKOUT_TOKEN="test", PAGBANK_RECURRING_TOKEN="test", PUBLIC_FRONTEND_URL="https://example.invalid", PUBLIC_API_URL="https://api.example.invalid", MERCHANT_LEGAL_NAME="Teste", MERCHANT_DOCUMENT="TESTE", MERCHANT_CONTACT_EMAIL="support@example.invalid", MERCHANT_ADDRESS="")
    def test_missing_supplier_address_prevents_checkout_activation(self):
        self.assertFalse(ready())
