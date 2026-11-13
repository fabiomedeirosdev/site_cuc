import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.serializers import account_data
from apps.accounts.views import AccountAPIView
from .access import account_subscription, has_access
from .models import Checkout, ConsumerRequest, EmailJob, Subscription
from .provider import PagBank, ProviderUnavailable, ready
from .services import complete_invitation, queue_email, synchronize, valid_invitation


class AcceptSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    legal_version = serializers.CharField(max_length=40)

    def validate(self, attrs):
        if not attrs["accepted"] or attrs["legal_version"] != settings.BILLING_LEGAL_VERSION:
            raise serializers.ValidationError("Leia e aceite a versão atual dos termos e da privacidade.")
        return attrs


class RegistrationSerializer(AcceptSerializer):
    token = serializers.CharField(max_length=128, trim_whitespace=False)
    name = serializers.CharField(max_length=150, required=False, default="", allow_blank=True)
    password = serializers.CharField(max_length=1024, required=False, default="", allow_blank=True, write_only=True, trim_whitespace=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"detail": "Campos de cadastro não permitidos."})
        return super().to_internal_value(data)


class BillingConfigView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"available": ready(), "sandbox": settings.PAGBANK_ENVIRONMENT == "sandbox", "amount": settings.SUBSCRIPTION_AMOUNT_CENTS, "currency": "BRL", "interval": "month", "legal_version": settings.BILLING_LEGAL_VERSION, "merchant": {"name": settings.MERCHANT_LEGAL_NAME, "document": settings.MERCHANT_DOCUMENT, "email": settings.MERCHANT_CONTACT_EMAIL, "address": settings.MERCHANT_ADDRESS}})


class CheckoutView(AccountAPIView):
    permission_classes = [AllowAny]
    throttle_scope = "checkout"

    def post(self, request):
        serializer = AcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not ready():
            return Response({"detail": "As assinaturas ainda não foram ativadas. Nenhuma cobrança foi realizada."}, status=503)
        if has_access(request.user):
            return Response({"detail": "Sua conta já tem um período de acesso válido. Consulte sua assinatura antes de contratar novamente."}, status=400)
        identifier = request.session.get("billing_checkout")
        checkout = Checkout.objects.filter(pk=identifier, created_at__gt=timezone.now() - timedelta(minutes=30), legal_version=settings.BILLING_LEGAL_VERSION).first() if identifier else None
        if not checkout:
            checkout = Checkout.objects.create(amount=settings.SUBSCRIPTION_AMOUNT_CENTS, legal_version=settings.BILLING_LEGAL_VERSION)
            request.session["billing_checkout"] = str(checkout.pk)
        if checkout.payment_url:
            return Response({"url": checkout.payment_url})
        try:
            data = PagBank().create_checkout(checkout)
        except ProviderUnavailable as error:
            return Response({"detail": str(error)}, status=503)
        checkout.provider_id = data["id"]
        checkout.plan_id = data["plan_id"]
        checkout.payment_url = data["url"]
        checkout.save(update_fields=["provider_id", "plan_id", "payment_url"])
        return Response({"url": checkout.payment_url}, status=201)


@method_decorator(never_cache, name="dispatch")
class PagBankWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "billing_webhook"

    def post(self, request):
        if not settings.BILLING_ENABLED:
            return Response({"detail": "Integração indisponível."}, status=503)
        if len(request.body) > 65536 or not isinstance(request.data, dict):
            return Response(status=400)
        event = request.data.get("event", "")
        resource = request.data.get("resource")
        if not isinstance(event, str) or not event.startswith("subscription.") or not isinstance(resource, dict):
            return Response({"received": True, "processed": False}, status=202)
        identifier = resource.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"SUBS_[A-Fa-f0-9-]{36}", identifier):
            return Response(status=400)
        try:
            subscription = synchronize(identifier)
        except ProviderUnavailable:
            return Response({"detail": "Confirmação financeira temporariamente indisponível."}, status=503)
        return Response({"received": True, "processed": subscription is not None})


@method_decorator(sensitive_post_parameters("token"), name="dispatch")
class InvitationCheckView(AccountAPIView):
    permission_classes = [AllowAny]
    throttle_scope = "invitation"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise serializers.ValidationError({"detail": "Informe um convite válido."})
        invitation = valid_invitation(request.data.get("token"))
        return Response({"email": invitation.subscription.email, "existing_account": get_user_model().objects.filter(email__iexact=invitation.subscription.email).exists(), "legal_version": settings.BILLING_LEGAL_VERSION})


@method_decorator(sensitive_post_parameters("token", "password"), name="dispatch")
class CompleteRegistrationView(AccountAPIView):
    permission_classes = [AllowAny]
    throttle_scope = "invitation"

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        account = complete_invitation(data["token"], data["name"], data["password"], user=request.user)
        login(request, account, backend="apps.accounts.backends.EmailBackend")
        return Response({"user": account_data(account)})


class ResendInvitationView(AccountAPIView):
    permission_classes = [AllowAny]
    throttle_scope = "invitation"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise serializers.ValidationError({"detail": "Informe um e-mail válido."})
        field = serializers.EmailField(max_length=254)
        email = field.run_validation(request.data.get("email")).lower()
        import hashlib
        key = "billing-invitation:" + hashlib.sha256(email.encode()).hexdigest()
        if cache.add(key, True, 900):
            for subscription in Subscription.objects.filter(email__iexact=email, user__isnull=True, paid_until__gt=timezone.now(), safety_hold=False):
                queue_email(subscription, "invitation", f"resend:{subscription.pk}:{timezone.now().strftime('%Y%m%d%H%M')}")
        return Response({"detail": "Se houver um pagamento confirmado pendente de cadastro, enviaremos um novo link para esse e-mail."})


class MySubscriptionsView(AccountAPIView):
    def get(self, request):
        subscriptions = Subscription.objects.filter(user=request.user).order_by("-created_at")
        rows = []
        for row in subscriptions:
            requests = [{"id": item.pk, "kind": item.kind, "created_at": item.created_at, "resolved": item.resolved_at is not None} for item in row.consumer_requests.order_by("-created_at")[:10]]
            rows.append({"id": row.pk, "status": row.status, "access_until": row.paid_until, "cancel_requested": row.cancel_requested_at is not None, "can_cancel": row.status not in {"CANCELED", "EXPIRED"}, "requests": requests})
        return Response({**account_subscription(request.user), "subscriptions": rows})


class CancelSubscriptionView(AccountAPIView):
    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
        if subscription.status in {"CANCELED", "EXPIRED"}:
            return Response({"detail": "A renovação dessa assinatura já está encerrada.", "access_until": subscription.paid_until})
        if not settings.BILLING_ENABLED:
            return Response({"detail": "O cancelamento financeiro está temporariamente indisponível. Use o canal de atendimento indicado nos termos."}, status=503)
        # Registrar o pedido antes de contactar o banco permite retentativa pelo operador.
        if not subscription.cancel_requested_at:
            subscription.cancel_requested_at = timezone.now()
            subscription.save(update_fields=["cancel_requested_at", "updated_at"])
        try:
            PagBank().cancel(subscription.provider_id)
        except ProviderUnavailable:
            return Response({"detail": "Seu pedido foi registrado, mas o banco ainda não confirmou o cancelamento. Tente novamente ou contate o atendimento."}, status=503)
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
            subscription.status = "CANCELED"
            subscription.canceled_at = timezone.now()
            subscription.save(update_fields=["status", "canceled_at", "updated_at"])
            queue_email(subscription, "cancellation", f"cancellation:{subscription.pk}")
        return Response({"detail": "Renovação cancelada. Seu acesso permanece até o fim do período já pago.", "access_until": subscription.paid_until})


class ConsumerRequestView(AccountAPIView):
    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
        if not isinstance(request.data, dict):
            raise serializers.ValidationError({"detail": "Informe uma solicitação válida."})
        kind = serializers.ChoiceField(choices=["withdrawal", "privacy"]).run_validation(request.data.get("kind"))
        message = serializers.CharField(max_length=4000, required=False, allow_blank=True).run_validation(request.data.get("message", ""))
        with transaction.atomic():
            existing = ConsumerRequest.objects.filter(subscription=subscription, kind=kind, resolved_at__isnull=True).first()
            if existing:
                return Response({"protocol": existing.pk, "detail": "Sua solicitação já está registrada."})
            item = ConsumerRequest.objects.create(subscription=subscription, kind=kind, message=message)
            queue_email(subscription, "consumer_request", f"request:{item.pk}")
        return Response({"protocol": item.pk, "detail": "Solicitação registrada. O atendimento dará continuidade ao pedido. Esse protocolo não significa que um estorno já foi efetuado."}, status=201)
