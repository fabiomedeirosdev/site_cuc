from django.conf import settings
from django.db import models
from django.utils import timezone


class PushSubscription(models.Model):
    endpoint_hash = models.CharField(max_length=64, unique=True)
    endpoint = models.URLField(max_length=2048)
    p256dh = models.CharField(max_length=100)
    auth = models.CharField(max_length=32)
    device_hash = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PushNotification(models.Model):
    kind = models.CharField(max_length=12, choices=[("article", "Publicação"), ("event", "Evento")])
    object_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_subscription_id = models.PositiveBigIntegerField(default=0)
    max_subscription_id = models.PositiveBigIntegerField(default=0)
    expanded = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["kind", "object_id"], name="webpush_unique_publication")]


class PushDelivery(models.Model):
    notification = models.ForeignKey(PushNotification, on_delete=models.CASCADE)
    subscription = models.ForeignKey(PushSubscription, on_delete=models.CASCADE)
    status = models.CharField(max_length=12, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notification", "subscription"], name="webpush_unique_delivery")]
