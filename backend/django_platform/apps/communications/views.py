import hashlib
import base64
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from apps.editorial.policies import public_name
from .models import Campaign, Delegation, Delivery, Event, NewsletterPreference, NewsletterSettings, Notice
from .policies import can_coordinate, can_manage, candidates, can_delegate, facilitator_users
from .serializers import CampaignSerializer, EventSerializer, PublicEventSerializer, PublicNoticeSerializer, NewsletterSettingsSerializer, NoticeSerializer
from .services import email_available, preference_for_user, render_campaign, request_confirmation


def paginated(request, data):
    paginator = PageNumberPagination()
    return paginator.get_paginated_response(paginator.paginate_queryset(data, request))


class PublicEventsView(AccountAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Event.objects.filter(is_published=True)
        current = Q(ends_at__gte=timezone.now()) | Q(ends_at__isnull=True, starts_at__gte=timezone.now())
        queryset = queryset.exclude(current).order_by("-starts_at") if request.query_params.get("past") == "1" else queryset.filter(current)
        return paginated(request, PublicEventSerializer(queryset, many=True, context={"request": request}).data)


class PublicMuralView(AccountAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Eventos não são copiados: toda atualização publicada aparece no mural.
        items = [{"kind": "event", **row} for row in PublicEventSerializer(Event.objects.filter(is_published=True), many=True, context={"request": request}).data]
        items += [{"kind": "notice", **row} for row in PublicNoticeSerializer(Notice.objects.filter(is_published=True), many=True, context={"request": request}).data]
        return paginated(request, sorted(items, key=lambda item: item["updated_at"], reverse=True))


class ManagementView(AccountAPIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not can_manage(request.user):
            raise PermissionDenied("A coordenação precisa autorizar sua participação na agenda, no mural e na newsletter.")


class DelegationView(ManagementView):
    def get(self, request):
        if not can_delegate(request.user):
            return Response({"can_delegate": False, "candidates": [], "delegations": []})
        people = [{"id": u.pk, "name": public_name(u)} for u in facilitator_users().select_related("profile")]
        rows = list(Delegation.objects.filter(coordinator__is_active=True).values("facilitator_id", "coordinator_id", "can_edit_agenda", "can_edit_mural", "can_edit_newsletter"))
        return Response({"can_delegate": True, "candidates": people, "delegations": rows})

    @transaction.atomic
    def put(self, request):
        if not can_delegate(request.user):
            raise PermissionDenied("Somente desenvolvedores e fundadores podem administrar delegações.")
        allowed = {"facilitator", "can_edit_agenda", "can_edit_mural"}
        if not isinstance(request.data, dict) or set(request.data) != allowed:
            raise ValidationError({"detail": "Informe o(a) facilitador(a) e as duas permissões independentes."})
        identifier = serializers.IntegerField(min_value=1).run_validation(request.data["facilitator"])
        person = get_object_or_404(facilitator_users(), pk=identifier)
        flags = {key: serializers.BooleanField().run_validation(request.data[key]) for key in allowed - {"facilitator"}}
        # Administradores podem revogar também autorizações antigas, sem apagar registros.
        Delegation.objects.filter(facilitator=person).update(**flags)
        delegation, _ = Delegation.objects.get_or_create(coordinator=request.user, facilitator=person, defaults={**flags, "can_edit_newsletter": False})
        for name, value in flags.items():
            setattr(delegation, name, value)
        delegation.save(update_fields=[*flags, "updated_at"])
        return self.get(request)


class ContentManagementView(ManagementView):
    models = {"events": (Event, EventSerializer), "notices": (Notice, NoticeSerializer), "campaigns": (Campaign, CampaignSerializer)}

    def pair(self, kind):
        if not can_manage(self.request.user, kind):
            raise PermissionDenied("Você não tem autorização para editar esta seção.")
        if kind not in self.models:
            from django.http import Http404
            raise Http404
        return self.models[kind]

    def get(self, request, kind, pk=None):
        model, serializer = self.pair(kind)
        return Response(serializer(get_object_or_404(model, pk=pk)).data) if pk else paginated(request, serializer(model.objects.all(), many=True).data)

    def post(self, request, kind, pk=None):
        if pk is not None:
            raise MethodNotAllowed("POST")
        _, serializer = self.pair(kind)
        form = serializer(data=request.data)
        form.is_valid(raise_exception=True)
        form.save(created_by=request.user)
        return Response(form.data, status=201)

    def patch(self, request, kind, pk=None):
        if pk is None:
            raise MethodNotAllowed("PATCH")
        model, serializer = self.pair(kind)
        with transaction.atomic():
            item = get_object_or_404(model.objects.select_for_update(), pk=pk)
            cancelling = isinstance(request.data, dict) and request.data == {"status": "cancelled"}
            if isinstance(item, Campaign) and (item.status in {"sent", "cancelled"} or item.status == "sending" and not cancelling):
                raise ValidationError({"detail": "Uma edição em envio ou concluída não pode ser alterada."})
            form = serializer(item, data=request.data, partial=True)
            form.is_valid(raise_exception=True)
            form.save(**({"error": "", "created_by": request.user} if isinstance(item, Campaign) else {}))
            if isinstance(item, Campaign) and item.status == "cancelled":
                item.deliveries.filter(status="pending").update(status="skipped")
        return Response(form.data)

    def delete(self, request, kind, pk=None):
        if pk is None:
            raise MethodNotAllowed("DELETE")
        model, _ = self.pair(kind)
        with transaction.atomic():
            item = get_object_or_404(model.objects.select_for_update(), pk=pk)
            if isinstance(item, Campaign) and item.status != "draft":
                raise ValidationError({"detail": "Somente rascunhos podem ser excluídos. Cancele o agendamento antes."})
            item.delete()
        return Response(status=204)


class PreviewView(ManagementView):
    def post(self, request):
        if not can_manage(request.user, "campaigns"):
            raise PermissionDenied()
        data = request.data.copy()
        identifier = data.get("campaign_id")
        data.pop("campaign_id", None)
        existing = get_object_or_404(Campaign, pk=serializers.IntegerField(min_value=1).run_validation(identifier)) if identifier else None
        form = CampaignSerializer(existing, data=data, partial=bool(existing))
        form.is_valid(raise_exception=True)
        values = dict(form.validated_data)
        remove_image = values.pop("remove_image", False)
        campaign = Campaign(**{**({"subject": existing.subject, "introduction": existing.introduction, "image": existing.image, "image_alt": existing.image_alt, "is_members_only": existing.is_members_only} if existing else {}), **values})
        if remove_image:
            campaign.image = ""
        image_url = None
        if campaign.image:
            with campaign.image.open("rb") as photo:
                image_url = "data:image/jpeg;base64," + base64.b64encode(photo.read()).decode("ascii")
        return Response({"html": render_campaign(campaign, image_url=image_url)})


class CommunicationImageView(AccountAPIView):
    permission_classes = [AllowAny]

    def get(self, request, kind, pk):
        from apps.billing.access import has_access
        models = {"notices": Notice, "campaigns": Campaign, "weekly": NewsletterSettings}
        if kind not in models:
            raise Http404
        item = get_object_or_404(models[kind], pk=pk)
        published = item.is_published if kind == "notices" else item.status == "sent" if kind == "campaigns" else False
        if not can_manage(request.user, "notices" if kind == "notices" else "campaigns") and (not published or item.is_members_only and not has_access(request.user)):
            raise Http404
        if not item.image:
            raise Http404
        try:
            response = FileResponse(item.image.open("rb"), content_type="image/jpeg")
        except FileNotFoundError:
            raise Http404
        response["X-Content-Type-Options"] = "nosniff"
        return response


class WeeklySettingsView(ManagementView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not can_manage(request.user, "campaigns"):
            raise PermissionDenied()

    def get(self, request):
        config, _ = NewsletterSettings.objects.get_or_create(pk=1)
        return Response({**NewsletterSettingsSerializer(config).data, "delivery_available": email_available()})

    def put(self, request):
        config, _ = NewsletterSettings.objects.get_or_create(pk=1)
        form = NewsletterSettingsSerializer(config, data=request.data)
        form.is_valid(raise_exception=True)
        form.save(updated_by=request.user)
        if not form.validated_data["weekly_enabled"]:
            Campaign.objects.filter(weekly_key__isnull=False, status__in=["scheduled", "sending"]).update(status="cancelled")
            Delivery.objects.filter(campaign__weekly_key__isnull=False, campaign__status="cancelled", status="pending").update(status="skipped")
        return self.get(request)


class PreferenceView(AccountAPIView):
    def get(self, request):
        preference = preference_for_user(request.user)
        return Response({"opted_in": preference.opted_in})

    def put(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {"opted_in"}:
            raise ValidationError({"detail": "Informe somente sua preferência de newsletter."})
        value = serializers.BooleanField().run_validation(request.data["opted_in"])
        preference = preference_for_user(request.user)
        preference.opted_in = value
        preference.confirmation_hash = ""
        preference.save()
        return Response({"opted_in": value})


class NewsletterRequestView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "newsletter"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Informe um e-mail válido."})
        email = serializers.EmailField(max_length=254).run_validation(request.data.get("email")).strip().lower()
        if request.data.get("accepted") is not True:
            raise ValidationError({"accepted": "Autorize o recebimento da newsletter semanal."})
        if not email_available():
            return Response({"detail": "A newsletter está em configuração. Nenhum e-mail foi enviado. Quem já tem conta pode salvar sua preferência por lá."}, status=503)
        try:
            request_confirmation(email)
        except Exception:
            # Não revelar se um endereço já consta na lista ou possui conta.
            pass
        return Response({"detail": "Solicitação recebida. Se ainda não recebe nossas novidades, enviaremos um link de confirmação por e-mail. Confira também a pasta de spam."})


class NewsletterActionView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "newsletter"

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Link inválido."})
        token = request.data.get("token")
        action = request.data.get("action")
        if action == "unsubscribe":
            try:
                identifier = UUID(str(token))
            except (TypeError, ValueError):
                raise ValidationError({"detail": "Link inválido."})
            NewsletterPreference.objects.filter(unsubscribe_token=identifier).update(opted_in=False, confirmation_hash="", updated_at=timezone.now())
            return Response({"detail": "Você deixou de receber a newsletter. Sua assinatura e seu acesso continuam inalterados."})
        if action != "confirm" or not isinstance(token, str) or not 40 <= len(token) <= 128:
            raise ValidationError({"detail": "Link inválido."})
        with transaction.atomic():
            preference = NewsletterPreference.objects.select_for_update().filter(confirmation_hash=hashlib.sha256(token.encode()).hexdigest(), confirmation_expires_at__gt=timezone.now()).first()
            if not preference:
                raise ValidationError({"detail": "Link inválido ou expirado. Solicite uma nova confirmação."})
            preference.opted_in = True
            preference.confirmation_hash = ""
            preference.save()
        return Response({"detail": "Recebimento da newsletter confirmado. Você pode sair a qualquer momento pelo link em cada e-mail."})
