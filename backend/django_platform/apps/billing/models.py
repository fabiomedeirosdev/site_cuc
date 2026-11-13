import uuid

from django.conf import settings
from django.db import models


class Checkout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_id = models.CharField(max_length=80, unique=True, null=True)
    plan_id = models.CharField(max_length=80, unique=True, null=True)
    payment_url = models.URLField(max_length=1000, blank=True)
    amount = models.PositiveIntegerField(default=4820)
    legal_version = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_id = models.CharField(max_length=80, unique=True)
    checkout = models.ForeignKey(Checkout, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")
    email = models.EmailField()
    status = models.CharField(max_length=30, default="PENDING")
    paid_until = models.DateTimeField(null=True, blank=True)
    provider_updated_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    safety_hold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "paid_until"])]
        verbose_name = "assinatura"
        verbose_name_plural = "assinaturas"


class PaidPeriod(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="paid_periods")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["subscription", "ends_at"], name="billing_unique_paid_period")]


class Invitation(models.Model):
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="invitation")
    token_hash = models.CharField(max_length=64, unique=True, null=True)
    expires_at = models.DateTimeField(null=True)
    consumed_at = models.DateTimeField(null=True)


class EmailJob(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    deduplication_key = models.CharField(max_length=180, unique=True)
    sent_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ConsumerRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="consumer_requests")
    kind = models.CharField(max_length=20, choices=[("withdrawal", "Arrependimento / reembolso"), ("privacy", "Direitos sobre dados pessoais")])
    message = models.TextField(max_length=4000, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LegalAcceptance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.CharField(max_length=40)
    source = models.CharField(max_length=30)
    accepted_at = models.DateTimeField(auto_now_add=True)
