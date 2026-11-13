import calendar
import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as ApiValidationError

from .access import has_access
from .models import Checkout, EmailJob, Invitation, LegalAcceptance, PaidPeriod, Subscription
from .provider import PagBank, ProviderUnavailable


def queue_email(subscription, kind, key):
    job, _ = EmailJob.objects.get_or_create(deduplication_key=key, defaults={"subscription": subscription, "kind": kind})
    transaction.on_commit(lambda: deliver_email(job.pk))


def deliver_email(job_id):
    try:
        with transaction.atomic():
            job = EmailJob.objects.select_for_update().select_related("subscription").get(pk=job_id)
            if job.sent_at:
                return
            subscription = job.subscription
            if job.kind == "invitation":
                invitation, _ = Invitation.objects.get_or_create(subscription=subscription)
                if invitation.consumed_at or not subscription.paid_until or subscription.paid_until <= timezone.now() or subscription.safety_hold:
                    job.sent_at = timezone.now()
                    job.save(update_fields=["sent_at"])
                    return
                raw = secrets.token_urlsafe(48)
                invitation.token_hash = hashlib.sha256(raw.encode()).hexdigest()
                invitation.expires_at = timezone.now() + timedelta(hours=48)
                invitation.save()
                link = settings.PUBLIC_FRONTEND_URL + "/cadastro.html#convite=" + raw
                subject = "Seu acesso à Comunidade Online Unidos em Cristo"
                body = f"Seu pagamento foi confirmado. Para criar ou vincular sua conta, abra:\n\n{link}\n\nEste link é pessoal, pode ser usado uma vez e vence em 48 horas. O período pago é contado pelo PagBank, não pela data do cadastro.\n\nAtendimento: {settings.MERCHANT_CONTACT_EMAIL}"
            else:
                subject = "Confirmação de solicitação — Comunidade Online"
                body = f"Recebemos sua solicitação. Protocolo: {job.deduplication_key}.\nO cancelamento da renovação preserva o acesso até o fim do período já pago.\nValidade registrada: {subscription.paid_until.isoformat() if subscription.paid_until else 'sem período pago'}.\nAtendimento: {settings.MERCHANT_CONTACT_EMAIL}"
            if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [subscription.email], fail_silently=False) != 1:
                raise RuntimeError("email_unavailable")
            job.sent_at = timezone.now()
            job.attempts += 1
            job.last_error = ""
            job.save(update_fields=["sent_at", "attempts", "last_error"])
    except Exception:
        EmailJob.objects.filter(pk=job_id, sent_at__isnull=True).update(last_error="email_unavailable")


def synchronize(identifier, provider=None):
    # Uma notificação nunca comprova pagamento: consultar a API autenticada primeiro.
    snapshot = (provider or PagBank()).subscription(identifier)
    try:
        validate_email(snapshot.email)
    except ValidationError:
        raise ProviderUnavailable("E-mail financeiro inválido.")
    with transaction.atomic():
        checkout = Checkout.objects.filter(plan_id=snapshot.plan_id).first()
        if not checkout:
            return None
        if snapshot.amount != checkout.amount or snapshot.currency != "BRL":
            raise ProviderUnavailable("Valor ou moeda da assinatura não confere.")
        subscription, _ = Subscription.objects.get_or_create(provider_id=snapshot.provider_id, defaults={"checkout": checkout, "email": snapshot.email})
        subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
        if subscription.checkout_id != checkout.pk or subscription.email != snapshot.email:
            raise ProviderUnavailable("A identidade financeira da assinatura mudou. Necessária conferência.")
        if subscription.provider_updated_at and snapshot.updated_at < subscription.provider_updated_at:
            return subscription
        if subscription.status in {"CANCELED", "EXPIRED"} and snapshot.status not in {subscription.status, "CANCELED", "EXPIRED"}:
            raise ProviderUnavailable("Uma assinatura encerrada não pode ser reativada.")
        subscription.status = snapshot.status
        subscription.provider_updated_at = snapshot.updated_at
        if snapshot.status == "CANCELED" and not subscription.canceled_at:
            subscription.canceled_at = timezone.now()
        if snapshot.status == "ACTIVE":
            end = snapshot.paid_until
            if not end or end <= snapshot.created_at or end > timezone.now() + timedelta(days=40):
                raise ProviderUnavailable("Ciclo mensal não reconhecido. Necessária conferência.")
            month = end.month - 1 or 12
            year = end.year - (end.month == 1)
            start = max(snapshot.created_at, end.replace(year=year, month=month, day=min(end.day, calendar.monthrange(year, month)[1])))
            PaidPeriod.objects.get_or_create(subscription=subscription, ends_at=end, defaults={"starts_at": start})
            if not subscription.paid_until or end > subscription.paid_until:
                subscription.paid_until = end
        # Cancelamento, atraso ou suspensão nunca subtraem os dias já confirmados.
        subscription.save()
        if subscription.cancel_requested_at and subscription.status in {"CANCELED", "EXPIRED"}:
            queue_email(subscription, "cancellation", f"cancellation:{subscription.pk}")
        if subscription.user_id is None and subscription.paid_until and subscription.paid_until > timezone.now() and not subscription.safety_hold:
            queue_email(subscription, "invitation", f"initial:{subscription.pk}")
        return subscription


def valid_invitation(raw, lock=False):
    if not isinstance(raw, str) or not 40 <= len(raw) <= 128:
        raise ApiValidationError({"token": "Link inválido, expirado ou já utilizado."})
    queryset = Invitation.objects.select_related("subscription")
    if lock:
        queryset = queryset.select_for_update()
    invitation = queryset.filter(token_hash=hashlib.sha256(raw.encode()).hexdigest(), consumed_at__isnull=True, expires_at__gt=timezone.now(), subscription__paid_until__gt=timezone.now(), subscription__safety_hold=False).first()
    if not invitation:
        raise ApiValidationError({"token": "Link inválido, expirado ou já utilizado."})
    return invitation


@transaction.atomic
def complete_invitation(raw, name, password, user=None):
    invitation = valid_invitation(raw, lock=True)
    subscription = Subscription.objects.select_for_update().get(pk=invitation.subscription_id)
    User = get_user_model()
    existing = User.objects.filter(email__iexact=subscription.email).first()
    if existing:
        if not user or not user.is_authenticated or not user.is_active or user.pk != existing.pk:
            raise ApiValidationError({"detail": "Entre na conta desse e-mail para vincular a assinatura. A senha existente não será alterada."})
        account = user
    else:
        if not name.strip():
            raise ApiValidationError({"name": "Informe seu nome."})
        account = User(username=uuid4().hex, email=subscription.email)
        try:
            validate_password(password, account)
        except ValidationError as error:
            raise ApiValidationError({"password": error.messages})
        try:
            with transaction.atomic():
                account.set_password(password)
                account.save()
                account.profile.display_name = name.strip()
                account.profile.save()
        except IntegrityError:
            raise ApiValidationError({"detail": "Essa conta já existe. Entre para vincular a assinatura."})
    subscription.user = account
    subscription.save(update_fields=["user", "updated_at"])
    account.groups.add(Group.objects.get(name="Assinantes"))
    invitation.consumed_at = timezone.now()
    invitation.save(update_fields=["consumed_at"])
    LegalAcceptance.objects.create(user=account, version=settings.BILLING_LEGAL_VERSION, source="subscription_registration")
    return account
