import json
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from pywebpush import WebPushException, webpush
from requests.exceptions import RequestException

from apps.billing.access import has_access
from apps.communications.models import Event
from apps.communications.policies import can_manage
from apps.content.policies import published_articles
from apps.editorial.policies import is_editorial_admin
from .models import PushDelivery, PushNotification, PushSubscription
from .views import valid_endpoint


def active_user(subscription):
    user = subscription.user
    if not user or not user.is_active or not subscription.session_key:
        return None
    session = Session.objects.filter(session_key=subscription.session_key, expire_date__gt=timezone.now()).first()
    data = session.get_decoded() if session else {}
    if str(data.get("_auth_user_id")) != str(user.pk) or not constant_time_compare(data.get("_auth_user_hash", ""), user.get_session_auth_hash()):
        return None
    return user


def source(notification):
    if notification.kind == "article":
        return published_articles().filter(pk=notification.object_id).first()
    current = Q(ends_at__gte=timezone.now()) | Q(ends_at__isnull=True, starts_at__gte=timezone.now())
    return Event.objects.filter(current, pk=notification.object_id, is_published=True, is_cancelled=False).first()


def authorized(notification, item, subscription):
    restricted = item.audience == "members" if notification.kind == "article" else item.is_members_only
    if not restricted:
        return True
    user = active_user(subscription)
    return bool(user and (has_access(user) or (is_editorial_admin(user) if notification.kind == "article" else can_manage(user, "events"))))


def payload(notification):
    # Generic text also protects a lock screen after logout or a last-moment
    # audience change. Opening the URL uses the existing access checks.
    article = notification.kind == "article"
    return json.dumps({
        "title": "RHEMA CUC",
        "body": "Uma nova publicação está disponível na comunidade." if article else "Um novo evento está disponível na agenda da comunidade.",
        "url": f"/conteudos/{notification.object_id}" if article else f"/agenda.html#evento-{notification.object_id}",
        "tag": f"rhema-{notification.kind}-{notification.object_id}",
    }, ensure_ascii=False)


def run_push(batch_size=20, max_seconds=25):
    result = {"sent": 0, "skipped": 0, "invalid": 0, "retried": 0, "failed": 0, "queued": 0}
    if not (settings.WEBPUSH_ENABLED and settings.WEBPUSH_PUBLIC_KEY and settings.WEBPUSH_PRIVATE_KEY and settings.WEBPUSH_SUBJECT):
        return {**result, "disabled": True}
    # Session advisory lock prevents overlapping cron jobs; no transaction is
    # held open during network requests. A crashed process releases this lock.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [739214081])
        if not cursor.fetchone()[0]:
            return {**result, "busy": True}
    started = time.monotonic()
    try:
        remaining = batch_size
        for notification in PushNotification.objects.filter(expanded=False).order_by("pk")[:batch_size]:
            if remaining <= 0:
                break
            if notification.created_at < timezone.now() - timedelta(days=1):
                notification.expanded = True
                notification.save(update_fields=["expanded"])
                continue
            rows = list(PushSubscription.objects.filter(pk__gt=notification.last_subscription_id, pk__lte=notification.max_subscription_id).order_by("pk")[:remaining])
            item = source(notification)
            for subscription in rows:
                if item and authorized(notification, item, subscription):
                    _, created = PushDelivery.objects.get_or_create(notification=notification, subscription=subscription)
                    result["queued"] += int(created)
            remaining -= len(rows)
            notification.last_subscription_id = rows[-1].pk if rows else notification.max_subscription_id
            notification.expanded = not rows or notification.last_subscription_id >= notification.max_subscription_id
            notification.save(update_fields=["last_subscription_id", "expanded"])

        deliveries = PushDelivery.objects.filter(status="pending", next_attempt_at__lte=timezone.now()).select_related("notification").order_by("next_attempt_at", "pk")[:batch_size]
        for delivery in deliveries:
            if time.monotonic() - started >= max_seconds:
                break
            subscription = PushSubscription.objects.select_related("user").filter(pk=delivery.subscription_id).first()
            if not subscription:
                continue
            item = source(delivery.notification)
            if not item or delivery.notification.created_at < timezone.now() - timedelta(days=1) or not authorized(delivery.notification, item, subscription):
                delivery.status = "skipped"
                delivery.save(update_fields=["status"])
                result["skipped"] += 1
                continue
            if not valid_endpoint(subscription.endpoint):
                subscription.delete()
                result["invalid"] += 1
                continue
            delivery.attempts += 1
            try:
                webpush(
                    subscription_info={"endpoint": subscription.endpoint, "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
                    data=payload(delivery.notification), vapid_private_key=settings.WEBPUSH_PRIVATE_KEY,
                    vapid_claims={"sub": settings.WEBPUSH_SUBJECT}, ttl=300, timeout=5,
                )
            except (WebPushException, RequestException, OSError, ValueError) as error:
                response = getattr(error, "response", None)
                status = getattr(response, "status_code", None) or getattr(error, "status_code", None)
                if status in (404, 410):
                    subscription.delete()
                    result["invalid"] += 1
                    continue
                delivery.last_error = f"http_{status}" if status else type(error).__name__[:40]
                transient = status is None or status == 429 or status >= 500
                delivery.status = "pending" if transient and delivery.attempts < 5 else "failed"
                delivery.next_attempt_at = timezone.now() + timedelta(minutes=min(60, 2 ** delivery.attempts))
                result["retried" if delivery.status == "pending" else "failed"] += 1
            else:
                delivery.status, delivery.last_error = "sent", ""
                result["sent"] += 1
            delivery.save(update_fields=["attempts", "status", "next_attempt_at", "last_error"])
        return result
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [739214081])
