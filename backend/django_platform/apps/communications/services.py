import hashlib
import secrets
from copy import deepcopy
from datetime import timedelta
from zoneinfo import ZoneInfo
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail as django_send_mail
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework.exceptions import ValidationError

from .models import Campaign, Delivery, Event, NewsletterPreference, NewsletterSettings, Notice
from .policies import can_manage
from .images import image_path


def send_mail(subject, message, from_email, recipient_list, html_message=None, fail_silently=False, image=None):
    if not image:
        return django_send_mail(subject, message, from_email, recipient_list, html_message=html_message, fail_silently=fail_silently)
    email = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    email.attach_alternative(html_message, "text/html")
    with image.open("rb") as photo:
        attachment = MIMEImage(photo.read(), _subtype="jpeg")
    attachment.add_header("Content-ID", "<newsletter-hero>")
    attachment.add_header("Content-Disposition", "inline", filename="imagem-newsletter.jpg")
    email.attach(attachment)
    email.mixed_subtype = "related"
    return email.send(fail_silently=fail_silently)


def recipient_has_access(preference):
    from apps.billing.access import has_access
    user = preference.user if preference.user_id else get_user_model().objects.filter(email__iexact=preference.email, is_active=True).first()
    return has_access(user)


def email_available():
    return bool(settings.NEWSLETTER_ENABLED and (settings.DEBUG or (settings.EMAIL_HOST and settings.PUBLIC_FRONTEND_URL.startswith("https://") and settings.MERCHANT_CONTACT_EMAIL and settings.DEFAULT_FROM_EMAIL and not settings.DEFAULT_FROM_EMAIL.endswith(".invalid"))))


def digest_content():
    now = timezone.now()
    return {
        "events": [{"id": event.pk, "title": event.title, "date": timezone.localtime(event.starts_at, ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M"), "location": "Apenas para assinantes" if event.is_members_only else event.location, "cancelled": event.is_cancelled, "members_only": event.is_members_only} for event in Event.objects.filter(is_published=True, starts_at__gte=now, starts_at__lte=now + timedelta(days=14)).order_by("starts_at")[:8]],
        "notices": list(Notice.objects.filter(is_published=True).values("id", "title", "body", "is_members_only")[:4]),
    }


def render_campaign(campaign, unsubscribe_url=None, image_url=None):
    content = deepcopy(campaign.snapshot) if campaign.snapshot else digest_content()
    current_events = {event.pk: event for event in Event.objects.filter(pk__in=[row["id"] for row in content.get("events", []) if row.get("id")], is_published=True)}
    public_events = []
    for row in content.get("events", []):
        current = current_events.get(row.get("id"))
        if row.get("id") and not current:
            continue
        if current and (current.is_members_only or row.get("members_only")):
            row["location"] = "Apenas para assinantes"
        elif not current:
            # Edições antigas não tinham o ID: não expor um local cuja
            # visibilidade atual não pode ser conferida com segurança.
            row["location"] = "Confira os detalhes na agenda"
        public_events.append(row)
    content["events"] = public_events
    current_notices = {notice.pk: notice for notice in Notice.objects.filter(pk__in=[row["id"] for row in content.get("notices", []) if row.get("id")], is_published=True)}
    notices = []
    for row in content.get("notices", []):
        current = current_notices.get(row.get("id"))
        if not current:
            continue
        restricted = current.is_members_only or row.get("is_members_only", False)
        notices.append({"title": current.title, "body": "Aviso exclusivo para assinantes. Consulte os detalhes no mural." if restricted else current.body,
            "image_url": settings.PUBLIC_API_URL + image_path("notices", current) if current.image and not restricted else None,
            "image_alt": current.image_alt if not restricted else ""})
    content["notices"] = notices
    if image_url is None and campaign.pk and campaign.image:
        image_url = settings.PUBLIC_API_URL + image_path("campaigns", campaign)
    return render_to_string("communications/newsletter.html", {"subject": campaign.subject, "introduction": campaign.introduction,
        "image_url": image_url, "image_alt": campaign.image_alt, "is_members_only": campaign.is_members_only,
        "content": content, "base_url": settings.PUBLIC_FRONTEND_URL, "unsubscribe_url": unsubscribe_url, "contact": settings.MERCHANT_CONTACT_EMAIL})


@transaction.atomic
def preference_for_user(user):
    email = user.email.strip().lower()
    previous = NewsletterPreference.objects.filter(user=user).first()
    if previous and previous.email != email:
        previous.user = None
        previous.opted_in = False
        previous.confirmation_hash = ""
        previous.save()
    preference, _ = NewsletterPreference.objects.get_or_create(email=email, defaults={"user": user})
    if preference.user_id is not None and preference.user_id != user.pk:
        raise ValidationError({"detail": "Não foi possível vincular a preferência a esta conta. Contate o atendimento."})
    if preference.user_id is None:
        preference.user = user
        preference.save(update_fields=["user"])
    return preference


def request_confirmation(email):
    preference, _ = NewsletterPreference.objects.get_or_create(email=email.strip().lower())
    if preference.opted_in:
        return
    if preference.confirmation_expires_at and preference.confirmation_expires_at > timezone.now() + timedelta(hours=47):
        return
    raw = secrets.token_urlsafe(48)
    preference.confirmation_hash = hashlib.sha256(raw.encode()).hexdigest()
    preference.confirmation_expires_at = timezone.now() + timedelta(hours=48)
    preference.save()
    link = settings.PUBLIC_FRONTEND_URL + "/newsletter.html#confirmar=" + raw
    try:
        send_mail("Confirme as novidades da Comunidade Unidos em Cristo", f"Você solicitou a newsletter semanal. Para confirmar, abra:\n\n{link}\n\nO link vence em 48 horas. Se não solicitou, ignore este e-mail. Não é necessário pagar nem criar uma conta para receber nossas novidades.", settings.DEFAULT_FROM_EMAIL, [preference.email], fail_silently=False)
    except Exception:
        preference.confirmation_expires_at = timezone.now()
        preference.save(update_fields=["confirmation_expires_at"])
        raise


def run_newsletters():
    if not email_available():
        return {"enabled": False, "sent": 0, "failed": 0}
    # Um único trabalhador PostgreSQL por vez, inclusive entre servidores.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(737107)")
        locked = cursor.fetchone()[0]
    if not locked:
        return {"enabled": True, "busy": True, "sent": 0, "failed": 0}
    sent = failed = 0
    try:
        now = timezone.now()
        local = timezone.localtime(now, ZoneInfo("America/Sao_Paulo"))
        config = NewsletterSettings.objects.filter(pk=1, weekly_enabled=True).first()
        if config and can_manage(config.updated_by) and (local.weekday(), local.hour) >= (config.weekday, config.hour):
            year, week, _ = local.isocalendar()
            Campaign.objects.get_or_create(weekly_key=f"{year}-W{week:02d}", defaults={"subject": config.subject, "introduction": config.introduction,
                "image": config.image.name, "image_alt": config.image_alt, "is_members_only": config.is_members_only,
                "created_by": config.updated_by, "status": "scheduled", "scheduled_at": now})
        for identifier in Campaign.objects.filter(status="scheduled", scheduled_at__lte=now).values_list("pk", flat=True):
            with transaction.atomic():
                campaign = Campaign.objects.select_for_update().get(pk=identifier)
                if campaign.status != "scheduled":
                    continue
                if not can_manage(campaign.created_by):
                    campaign.status = "draft"
                    campaign.error = "Responsável sem permissão. Revise e agende novamente."
                    campaign.save()
                    continue
                campaign.snapshot = digest_content()
                campaign.status = "sending"
                campaign.error = ""
                campaign.save()
                preferences = NewsletterPreference.objects.filter(opted_in=True).select_related("user")
                if campaign.is_members_only:
                    preferences = [preference for preference in preferences if recipient_has_access(preference)]
                Delivery.objects.bulk_create([Delivery(campaign=campaign, preference=preference, email=preference.email) for preference in preferences], ignore_conflicts=True)
        for identifier in Delivery.objects.filter(status="pending", campaign__status="sending").values_list("pk", flat=True):
            with transaction.atomic():
                delivery = Delivery.objects.select_for_update(of=("self",)).select_related("campaign", "preference__user").get(pk=identifier)
                preference = delivery.preference
                automatic_stopped = bool(delivery.campaign.weekly_key) and not NewsletterSettings.objects.filter(pk=1, weekly_enabled=True).exists()
                identity_changed = preference.user_id and preference.user.email.strip().lower() != preference.email
                audience_denied = delivery.campaign.is_members_only and not recipient_has_access(preference)
                if automatic_stopped or delivery.campaign.status != "sending" or not preference.opted_in or identity_changed or audience_denied or preference.email != delivery.email.lower() or not can_manage(delivery.campaign.created_by):
                    delivery.status = "skipped"
                    delivery.save(update_fields=["status"])
                    continue
                delivery.attempts += 1
                try:
                    html = render_campaign(delivery.campaign, settings.PUBLIC_FRONTEND_URL + "/newsletter.html#sair=" + str(preference.unsubscribe_token), image_url="cid:newsletter-hero" if delivery.campaign.image else None)
                    if send_mail(delivery.campaign.subject, strip_tags(html), settings.DEFAULT_FROM_EMAIL, [delivery.email], html_message=html, fail_silently=False, image=delivery.campaign.image) != 1:
                        raise RuntimeError("email_unavailable")
                    delivery.status = "sent"
                    delivery.sent_at = timezone.now()
                    sent += 1
                except Exception:
                    failed += 1
                delivery.save()
        for campaign in Campaign.objects.filter(status="sending"):
            if not campaign.deliveries.filter(status="pending").exists():
                Campaign.objects.filter(pk=campaign.pk, status="sending").update(status="sent")
        return {"enabled": True, "sent": sent, "failed": failed}
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(737107)")
