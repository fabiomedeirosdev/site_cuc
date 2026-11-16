from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from uuid import uuid4
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from apps.accounts.policies import is_developer, profile_role
from .media import public_image_url
from apps.billing.models import ConsumerRequest, Subscription
from apps.communications.models import Campaign, Event, Notice
from apps.communications.policies import can_manage
from apps.content.models import Article
from apps.content.policies import editable_articles
from apps.content.serializers import ArticleEditorSerializer
from apps.content.views import with_relations
from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import can_create_groups, is_editorial_admin, managed_groups, public_name
from apps.editorial.images import clean_group_cover


def can_open_panel(user):
    return bool(user.is_authenticated and user.is_active and (
        is_editorial_admin(user) or editable_articles(user).exists()
        or user.editorial_memberships.filter(group__is_active=True).exists() or can_manage(user)
        or getattr(user.profile, "community_role", "") in {"columnist", "priest", "deacon"}
    ))


class PanelView(AccountAPIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not can_open_panel(request.user):
            raise PermissionDenied("Esta área é reservada à equipe autorizada.")


class AdminView(PanelView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_editorial_admin(request.user):
            raise PermissionDenied("Esta operação é exclusiva da administração.")


def paginate(request, queryset, transform):
    paginator = PageNumberPagination()
    rows = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([transform(row) for row in rows])


class DashboardView(PanelView):
    def get(self, request):
        articles = editable_articles(request.user)
        current = timezone.localdate()
        months = []
        for offset in range(5, -1, -1):
            absolute = current.year * 12 + current.month - 1 - offset
            year, month = divmod(absolute, 12)
            months.append(timezone.make_aware(datetime(year, month + 1, 1)))
        counts = {row["month"].strftime("%Y-%m"): row["total"] for row in articles.filter(
            status="published", published_at__gte=months[0]
        ).annotate(month=TruncMonth("published_at")).values("month").annotate(total=Count("pk"))}
        data = {
            "scope": "Todo o site" if is_editorial_admin(request.user) else "Sua área de atuação",
            "totals": {"contents": articles.count(), "published": articles.filter(status="published").count(),
                       "drafts": articles.filter(status="draft").count(), "featured": articles.filter(is_featured=True).count(),
                       "groups": managed_groups(request.user).count()},
            "activity": [{"month": month.strftime("%m/%Y"), "total": counts.get(month.strftime("%Y-%m"), 0)} for month in months],
            "recent": ArticleEditorSerializer(with_relations(articles).order_by("-updated_at")[:5], many=True).data,
        }
        if is_editorial_admin(request.user):
            data["totals"].update(users=get_user_model().objects.count(),
                subscriptions=Subscription.objects.filter(paid_until__gt=timezone.now(), safety_hold=False, user__is_active=True).values("user").distinct().count(),
                requests=ConsumerRequest.objects.filter(resolved_at__isnull=True).count())
        if can_manage(request.user):
            data["totals"].update(events=Event.objects.filter(is_published=True, is_cancelled=False, starts_at__gte=timezone.now()).count(),
                notices=Notice.objects.filter(is_published=True).count(), campaigns=Campaign.objects.count())
        return Response(data)


class HighlightInput(serializers.Serializer):
    is_featured = serializers.BooleanField(required=True)
    featured_position = serializers.IntegerField(min_value=0, max_value=32767, required=True)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"detail": "Campos de destaque inválidos."})
        return super().to_internal_value(data)


class HighlightView(PanelView):
    def get(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed("GET")
        articles = with_relations(Article.objects.filter(group__in=managed_groups(request.user))).order_by("-is_featured", "featured_position", "-updated_at", "-pk")
        return paginate(request, articles, lambda article: ArticleEditorSerializer(article).data)

    def patch(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed("PATCH")
        article = get_object_or_404(Article.objects.filter(group__in=managed_groups(request.user)), pk=pk)
        serializer = HighlightInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["is_featured"]:
            from apps.content.policies import published_articles
            if not published_articles().filter(pk=pk).exists() or not article.cover_id:
                raise serializers.ValidationError("Publique o conteúdo com uma capa em um grupo ativo antes de destacá-lo.")
        for field, value in serializer.validated_data.items():
            setattr(article, field, value)
        article.save(update_fields=["is_featured", "featured_position", "updated_at"])
        return Response(ArticleEditorSerializer(article).data)


class UsersView(AdminView):
    def get(self, request):
        users = get_user_model().objects.select_related("profile").order_by("-date_joined", "-pk")
        query = request.query_params.get("q", "")[:150]
        if query:
            users = users.filter(Q(email__icontains=query) | Q(profile__display_name__icontains=query))
        return paginate(request, users, lambda user: {"id": user.pk, "name": public_name(user), "email": user.email,
            "is_active": user.is_active, "is_administrator": is_editorial_admin(user),
            "access_protected": user.is_staff or is_editorial_admin(user) or user.pk == request.user.pk, "joined_at": user.date_joined,
            "role_label": profile_role(user)[1],
            "can_edit": not (user.is_superuser or user.profile.community_role == "developer") or is_developer(request.user),
            "can_delete": user.pk != request.user.pk and (not (user.is_superuser or user.profile.community_role == "developer") or is_developer(request.user))})


class UserAccessInput(serializers.Serializer):
    is_active = serializers.BooleanField()


class UserAccessView(AdminView):
    def delete(self, request, pk):
        from .team_views import TeamView
        return TeamView.delete(self, request, pk)

    def patch(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        if user.pk == request.user.pk or is_editorial_admin(user) or user.is_staff:
            raise PermissionDenied("Contas administrativas são protegidas contra alteração de acesso neste painel.")
        if set(request.data) != {"is_active"}:
            raise serializers.ValidationError("Informe apenas a situação de acesso.")
        serializer = UserAccessInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.is_active = serializer.validated_data["is_active"]
        user.save(update_fields=["is_active"])
        return Response({"id": user.pk, "is_active": user.is_active})


class SubscriptionsView(AdminView):
    def get(self, request):
        return paginate(request, Subscription.objects.order_by("-created_at", "-pk"), lambda row: {
            "id": row.pk, "email": row.email, "status": row.status, "paid_until": row.paid_until,
            "safety_hold": row.safety_hold, "cancel_requested_at": row.cancel_requested_at,
        })


class RequestsView(AdminView):
    def get(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed("GET")
        return paginate(request, ConsumerRequest.objects.select_related("subscription").order_by("resolved_at", "-created_at", "-pk"), lambda row: {
            "id": row.pk, "email": row.subscription.email, "kind": row.get_kind_display(),
            "message": row.message, "created_at": row.created_at, "resolved_at": row.resolved_at,
        })

    def patch(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed("PATCH")
        row = get_object_or_404(ConsumerRequest, pk=pk)
        if request.data != {"resolved": True}:
            raise serializers.ValidationError("Informe a conclusão do atendimento.")
        row.resolved_at = row.resolved_at or timezone.now()
        row.save(update_fields=["resolved_at"])
        return Response({"id": row.pk, "resolved_at": row.resolved_at})


class GroupInput(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=False, default=True)
    custom_cover = serializers.FileField(write_only=True, required=False)
    remove_custom_cover = serializers.BooleanField(write_only=True, required=False, default=False)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = EditorialGroup
        fields = ["id", "name", "slug", "description", "cover", "custom_cover", "remove_custom_cover", "cover_url", "cover_alt", "is_active", "position", "address", "whatsapp", "video_url"]
        read_only_fields = ["id", "slug", "cover_url"]

    def get_cover_url(self, obj):
        return public_image_url(obj.custom_cover)

    def validate_whatsapp(self, value):
        import re
        if value and not re.fullmatch(r"[0-9]{10,15}", value):
            raise serializers.ValidationError("Informe somente números, com código do país e DDD.")
        return value

    def validate_video_url(self, value):
        from apps.content.video import video_id
        identifier = video_id(value)
        return f"https://www.youtube.com/watch?v={identifier}" if identifier else ""

    def validate_custom_cover(self, upload):
        return clean_group_cover(upload)

    def validate(self, attrs):
        if attrs.get("custom_cover") and attrs.get("remove_custom_cover"):
            raise serializers.ValidationError({"custom_cover": "Escolha uma imagem própria ou uma imagem da comunidade."})
        has_custom = attrs.get("custom_cover") or (getattr(self.instance, "custom_cover", None) and not attrs.get("remove_custom_cover"))
        if has_custom and not attrs.get("cover_alt", getattr(self.instance, "cover_alt", "")).strip():
            raise serializers.ValidationError({"cover_alt": "Descreva a foto própria para quem usa leitor de tela."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("remove_custom_cover", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_custom_cover", False):
            validated_data["custom_cover"] = ""
            validated_data["cover_alt"] = ""
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - (set(self.fields) - set(self.Meta.read_only_fields)):
            raise serializers.ValidationError({"detail": "Campos de grupo inválidos."})
        return super().to_internal_value(data)


class GroupSettingsView(PanelView):
    def get(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed("GET")
        return Response(GroupInput(managed_groups(request.user), many=True).data)

    @transaction.atomic
    def post(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed("POST")
        if not can_create_groups(request.user):
            raise PermissionDenied("Somente administradores e coordenadores podem criar grupos.")
        administrator = is_editorial_admin(request.user)
        if not administrator and set(request.data) & {"is_active", "position"}:
            raise PermissionDenied("Somente a administração pode definir a ativação e a ordem dos grupos.")
        serializer = GroupInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        slug = f"{slugify(serializer.validated_data['name'])[:120] or 'grupo'}-{uuid4().hex[:10]}"
        group = serializer.save(slug=slug)
        if not administrator:
            Membership.objects.create(group=group, user=request.user, role=Membership.Role.COORDINATOR)
        return Response(GroupInput(group).data, status=201)

    def patch(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed("PATCH")
        group = get_object_or_404(managed_groups(request.user), pk=pk)
        if not is_editorial_admin(request.user) and set(request.data) & {"is_active", "position"}:
            raise PermissionDenied("Somente a administração pode alterar a ativação e a ordem dos grupos.")
        serializer = GroupInput(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(GroupInput(serializer.save()).data)
