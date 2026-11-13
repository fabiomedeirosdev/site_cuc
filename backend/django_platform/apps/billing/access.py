from django.utils import timezone
from django.db.models import F

from .models import Subscription


def has_access(user):
    return bool(user and user.is_authenticated and user.is_active and Subscription.objects.filter(user=user, paid_until__gt=timezone.now(), safety_hold=False).exists())


def account_subscription(user):
    if not user.is_authenticated:
        return {"status": "none", "access_until": None, "has_access": False}
    rows = Subscription.objects.filter(user=user)
    subscription = rows.filter(paid_until__gt=timezone.now(), safety_hold=False).order_by("-paid_until").first() or rows.order_by(F("paid_until").desc(nulls_last=True), "-created_at").first()
    if not subscription:
        return {"status": "none", "access_until": None, "has_access": False}
    access = has_access(user)
    return {"status": "canceled_paid" if access and subscription.status == "CANCELED" else "active" if access else "expired" if subscription.paid_until else "pending", "access_until": subscription.paid_until, "has_access": access}
