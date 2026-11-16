import base64
import hashlib
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from .models import PushSubscription


def valid_endpoint(endpoint):
    try:
        url = urlsplit(endpoint)
        host = (url.hostname or "").lower()
        trusted = host in {"fcm.googleapis.com", "updates.push.services.mozilla.com", "push.services.mozilla.com"}
        trusted = trusted or host.endswith(".push.apple.com") or host.endswith(".notify.windows.com")
        return bool(trusted and url.scheme == "https" and url.port in (None, 443) and not url.username and not url.password and not url.fragment)
    except ValueError:
        return False


def decode_key(value, length):
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if len(decoded) != length:
            raise ValueError
        return decoded
    except (ValueError, TypeError):
        raise serializers.ValidationError("Chave de notificação inválida.")


class SubscriptionInput(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2048)
    device_token = serializers.RegexField(r"^[A-Za-z0-9_-]{43,128}$")
    p256dh = serializers.CharField(max_length=100, required=False)
    auth = serializers.CharField(max_length=32, required=False)

    def validate_endpoint(self, value):
        if not valid_endpoint(value):
            raise serializers.ValidationError("Serviço de notificações não permitido.")
        return value


class PushConfigView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "webpush"

    def get(self, request):
        enabled = bool(settings.WEBPUSH_ENABLED and settings.WEBPUSH_PUBLIC_KEY and settings.WEBPUSH_PRIVATE_KEY and settings.WEBPUSH_SUBJECT)
        return Response({"enabled": enabled, "public_key": settings.WEBPUSH_PUBLIC_KEY if enabled else None})


class SubscriptionView(AccountAPIView):
    permission_classes = [AllowAny]
    throttle_scope = "webpush"

    def values(self, request):
        if len(request.body) > 8192:
            raise ValidationError("Inscrição muito grande.")
        serializer = SubscriptionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        return values, hashlib.sha256(values["endpoint"].encode()).hexdigest(), hashlib.sha256(values["device_token"].encode()).hexdigest()

    @transaction.atomic
    def post(self, request):
        if not settings.WEBPUSH_ENABLED:
            return Response({"detail": "As notificações ainda não estão disponíveis."}, status=503)
        values, endpoint_hash, device_hash = self.values(request)
        public_key = decode_key(values.get("p256dh", ""), 65)
        try:
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key)
        except ValueError:
            raise ValidationError("Chave pública de notificação inválida.")
        decode_key(values.get("auth", ""), 16)
        subscription, _ = PushSubscription.objects.select_for_update().get_or_create(endpoint_hash=endpoint_hash, defaults={
            "endpoint": values["endpoint"], "device_hash": device_hash, "p256dh": values["p256dh"], "auth": values["auth"],
        })
        if not constant_time_compare(subscription.device_hash, device_hash):
            raise PermissionDenied("Esta inscrição pertence a outro dispositivo.")
        user = request.user if request.user.is_authenticated and request.user.is_active else None
        if user and not request.session.session_key:
            request.session.save()
        subscription.user = user
        subscription.session_key = request.session.session_key if user else ""
        subscription.p256dh, subscription.auth = values["p256dh"], values["auth"]
        subscription.save()
        return Response({"subscribed": True})

    @transaction.atomic
    def delete(self, request):
        values, endpoint_hash, device_hash = self.values(request)
        subscription = PushSubscription.objects.select_for_update().filter(endpoint_hash=endpoint_hash).first()
        if subscription:
            if not constant_time_compare(subscription.device_hash, device_hash):
                raise PermissionDenied("Esta inscrição pertence a outro dispositivo.")
            subscription.delete()
        return Response(status=204)
