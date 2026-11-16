from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Profile
from apps.accounts.views import AccountAPIView
from apps.billing.access import has_access
from apps.billing.models import ConsumerRequest
from apps.communications.models import Event, Notice
from apps.communications.policies import can_manage
from apps.content.policies import published_articles
from apps.editorial.policies import is_editorial_admin
from .models import IncomingMessage


def can_handle_inbox(user):
    return bool(user.is_authenticated and user.is_active and (
        is_editorial_admin(user)
        or getattr(getattr(user, "profile", None), "community_role", "") in {"columnist", "priest", "deacon", "administration"}
        or user.editorial_memberships.filter(group__is_active=True, role__in=["columnist", "coordinator"]).exists()
    ))


class NotificationsView(AccountAPIView):
    def get(self, request):
        if not request.user.is_active:
            raise PermissionDenied()
        now = timezone.now()
        since = now - timedelta(days=30)
        seen = request.user.profile.notifications_seen_at
        paid = has_access(request.user)
        admin = is_editorial_admin(request.user)
        articles = published_articles().filter(updated_at__gte=since, updated_at__lte=now)
        if not (paid or admin):
            articles = articles.filter(audience="public")
        events = Event.objects.filter(is_published=True, updated_at__gte=since, updated_at__lte=now)
        notices = Notice.objects.filter(is_published=True, updated_at__gte=since, updated_at__lte=now)
        if not (paid or can_manage(request.user, "events")):
            events = events.filter(is_members_only=False)
        if not (paid or can_manage(request.user, "notices")):
            notices = notices.filter(is_members_only=False)
        rows = []
        unread = 0
        sources = [(articles, "article", "Conteúdo", lambda row: f"/conteudos/{row.pk}"),
                   (events, "event", "Agenda", lambda row: f"/agenda.html#evento-{row.pk}"),
                   (notices, "notice", "Mural", lambda row: "/mural.html")]
        for queryset, kind, label, link in sources:
            unread += queryset.filter(updated_at__gt=seen).count() if seen else queryset.count()
            for row in queryset.order_by("-updated_at", "-pk")[:20]:
                rows.append({"id": f"{kind}-{row.pk}", "kind": kind, "label": label, "title": row.title,
                             "url": link(row), "at": row.updated_at, "unread": seen is None or row.updated_at > seen, "pending": False})
        rows.sort(key=lambda row: (row["at"], row["id"]), reverse=True)
        pending = []
        pending_count = 0
        if can_handle_inbox(request.user):
            messages = IncomingMessage.objects.filter(responded_at__isnull=True, received_at__lte=now)
            pending_count += messages.count()
            pending += [{"id": f"email-{row.pk}", "kind": "email", "label": "E-mail · Resposta pendente",
                         "title": row.subject, "url": f"/painel/mensagens?mensagem={row.pk}", "at": row.received_at,
                         "unread": True, "pending": True} for row in messages[:10]]
        if admin:
            requests = ConsumerRequest.objects.filter(resolved_at__isnull=True, created_at__lte=now).order_by("-created_at", "-pk")
            pending_count += requests.count()
            pending += [{"id": f"request-{row.pk}", "kind": "request", "label": "Atendimento pendente",
                         "title": row.get_kind_display(), "url": "/painel/atendimentos", "at": row.created_at,
                         "unread": True, "pending": True} for row in requests[:10]]
        pending.sort(key=lambda row: (row["at"], row["id"]), reverse=True)
        return Response({"as_of": now, "unread_count": unread, "pending_count": pending_count,
                         "updates": rows[:20], "pending": pending[:20]})

    @transaction.atomic
    def post(self, request):
        if not request.user.is_active:
            raise PermissionDenied()
        if not isinstance(request.data, dict) or set(request.data) != {"seen_until"}:
            raise ValidationError("Informe a data das notificações visualizadas.")
        seen = serializers.DateTimeField().run_validation(request.data["seen_until"])
        if seen > timezone.now():
            raise ValidationError("Data de leitura inválida.")
        profile = Profile.objects.select_for_update().get(user=request.user)
        if profile.notifications_seen_at is None or seen > profile.notifications_seen_at:
            profile.notifications_seen_at = seen
            profile.save(update_fields=["notifications_seen_at"])
        return Response({"seen_until": profile.notifications_seen_at})


class InboxView(AccountAPIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not can_handle_inbox(request.user):
            raise PermissionDenied("Esta área é reservada à equipe de atendimento da comunidade.")

    def get(self, request, pk=None):
        from rest_framework.pagination import PageNumberPagination
        from .inbox import webmail_url
        def row(message, detail=False):
            data = {"id": message.pk, "subject": message.subject, "sender": message.sender,
                    "received_at": message.received_at, "responded_at": message.responded_at}
            if detail:
                data["body"] = message.body
            return data
        if pk is not None:
            return Response(row(get_object_or_404(IncomingMessage, pk=pk), detail=True))
        messages = IncomingMessage.objects.all()
        if request.query_params.get("status", "pending") != "all":
            messages = messages.filter(responded_at__isnull=True)
        paginator = PageNumberPagination()
        result = paginator.get_paginated_response([row(message) for message in paginator.paginate_queryset(messages, request)])
        result.data["webmail_url"] = webmail_url()
        return result

    @transaction.atomic
    def patch(self, request, pk):
        if not isinstance(request.data, dict) or set(request.data) != {"responded"}:
            raise ValidationError("Informe somente a situação da resposta.")
        responded = serializers.BooleanField().run_validation(request.data["responded"])
        message = get_object_or_404(IncomingMessage.objects.select_for_update(), pk=pk)
        message.responded_at = (message.responded_at or timezone.now()) if responded else None
        message.responded_by = request.user if responded else None
        message.save(update_fields=["responded_at", "responded_by"])
        return Response({"id": message.pk, "responded_at": message.responded_at})
