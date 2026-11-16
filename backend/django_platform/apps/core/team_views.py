from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Profile
from apps.accounts.policies import is_developer, profile_role
from apps.accounts.serializers import ProfileUpdateSerializer
from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import public_name
from .management_views import AdminView, paginate


class TeamInput(serializers.Serializer):
    email = serializers.EmailField(required=False)
    display_name = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(max_length=1024, required=False, write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=["", "founder", "developer", "columnist", "coordinator", "administration", "priest", "deacon"], required=False)
    biography = serializers.CharField(max_length=3000, required=False, allow_blank=True)
    website = serializers.URLField(max_length=500, required=False, allow_blank=True)
    video_url = serializers.URLField(max_length=1000, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    group = serializers.PrimaryKeyRelatedField(queryset=EditorialGroup.objects.all(), allow_null=True, required=False)
    position = serializers.IntegerField(min_value=0, max_value=32767, required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError("Campos não permitidos.")
        return super().to_internal_value(data)


def team_row(profile):
    return {"id": profile.user_id, "display_name": public_name(profile.user), "email": profile.user.email,
            "role": profile_role(profile.user)[0], "community_role": profile.community_role, "position": profile.position, "biography": profile.biography, "website": profile.website,
            "video_url": profile.video_url, "first_name": profile.user.first_name, "last_name": profile.user.last_name}


class TeamMembershipInput(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(queryset=EditorialGroup.objects.all())
    role = serializers.ChoiceField(choices=Membership.Role.choices)

    def validate(self, attrs):
        if "group" not in attrs or "role" not in attrs:
            raise ValidationError("Informe o grupo e a função nesse grupo.")
        return attrs


class TeamUpdateInput(TeamInput):
    memberships = TeamMembershipInput(many=True, required=False)

    def validate_memberships(self, values):
        group_ids = [value["group"].pk for value in values]
        if len(group_ids) != len(set(group_ids)):
            raise ValidationError("Escolha cada grupo apenas uma vez.")
        return values


def team_detail(profile):
    return {
        **team_row(profile),
        "memberships": list(profile.user.editorial_memberships.values("group", "role")),
        "available_groups": list(EditorialGroup.objects.order_by("name", "pk").values("id", "name", "is_active")),
    }


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class TeamView(AdminView):
    def get(self, request, pk=None):
        profiles = Profile.objects.select_related("user").order_by("position", "pk")
        if pk is not None:
            return Response(team_detail(get_object_or_404(profiles, user_id=pk)))
        query = request.query_params.get("q", "").strip()[:150]
        if query:
            profiles = profiles.filter(Q(display_name__icontains=query) | Q(user__email__icontains=query))
        return paginate(request, profiles, team_row)

    def validate_input(self, request, partial=False):
        form = (TeamUpdateInput if partial else TeamInput)(data=request.data, partial=partial)
        form.is_valid(raise_exception=True)
        values = form.validated_data
        if values.get("role") == "developer" and not is_developer(request.user):
            raise PermissionDenied("Somente o(a) Desenvolvedor(a) pode atribuir essa função.")
        return values

    @transaction.atomic
    def post(self, request):
        values = self.validate_input(request)
        email = values.get("email", "").strip().lower()
        if not email:
            raise ValidationError({"email": "Informe o e-mail."})
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        password = values.get("password")
        if password:
            if user:
                raise ValidationError({"email": "A conta já existe. Use o vínculo sem definir senha."})
            if not values.get("display_name"):
                raise ValidationError({"display_name": "Informe o nome."})
            user = User(username=uuid4().hex, email=email)
            try:
                validate_password(password, user)
            except DjangoValidationError as error:
                raise ValidationError({"password": error.messages})
            user.set_password(password)
            user.save()
            user.profile.display_name = values["display_name"]
            user.profile.save(update_fields=["display_name"])
        if not user or not user.is_active:
            raise ValidationError({"email": "Informe uma conta ativa ou crie um novo acesso."})
        self.assign(request, user, values)
        return Response(team_row(user.profile), status=201)

    def assign(self, request, user, values):
        profile = user.profile
        if (user.is_superuser or profile.community_role == "developer") and not is_developer(request.user):
            raise PermissionDenied("Esta conta é administrada pelo(a) Desenvolvedor(a).")
        group = values.get("group")
        role = values.get("role")
        if group and not role:
            raise ValidationError({"role": "Selecione uma função para o vínculo com o grupo."})
        if role == "coordinator" and not group:
            raise ValidationError({"group": "Coordenadores mantêm o vínculo obrigatório com um grupo."})
        if role == "coordinator" and profile.community_role:
            raise ValidationError({"role": "Remova a função geral antes de atribuir a coordenação."})
        if role in {"founder", "developer", "columnist", "administration", "priest", "deacon", ""}:
            profile.community_role = role
        if "position" in values:
            profile.position = values["position"]
        profile.save(update_fields=["community_role", "position", "updated_at"])
        if group:
            group_role = "coordinator" if role == "coordinator" else "columnist"
            existing = Membership.objects.filter(group=group, user=user).first()
            if existing and existing.role != group_role:
                raise ValidationError({"group": "Edite a função do vínculo existente na equipe do grupo."})
            Membership.objects.get_or_create(group=group, user=user, defaults={"role": group_role})

    @transaction.atomic
    def patch(self, request, pk):
        if set(request.data) - {"role", "position", "display_name", "email", "biography", "website", "video_url", "first_name", "last_name", "memberships"}:
            raise ValidationError("Informe somente os dados editáveis do membro.")
        user = get_object_or_404(get_user_model().objects.select_related("profile"), pk=pk)
        values = self.validate_input(request, partial=True)
        self.assign(request, user, values)
        if "email" in values:
            email = values["email"].strip().lower()
            if get_user_model().objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                raise ValidationError({"email": "Este e-mail já está em uso."})
            user.email = email
            # Invalidate an earlier email change request after administrative edits.
            user.profile.pending_email = ""
            user.profile.email_change_hash = ""
            user.profile.email_change_auth_hash = ""
            user.profile.email_change_expires_at = None
            user.profile.save(update_fields=["pending_email", "email_change_hash", "email_change_auth_hash", "email_change_expires_at"])
        for field in ["first_name", "last_name"]:
            if field in values:
                setattr(user, field, values[field])
        user.save(update_fields=["email", "first_name", "last_name"])
        profile_data = {key: value for key, value in values.items() if key in {"display_name", "biography", "website", "video_url"}}
        form = ProfileUpdateSerializer(user.profile, data=profile_data, partial=True)
        form.is_valid(raise_exception=True)
        form.save()
        if "memberships" in values:
            memberships = values["memberships"]
            user.editorial_memberships.exclude(group_id__in=[value["group"].pk for value in memberships]).delete()
            for membership in memberships:
                Membership.objects.update_or_create(user=user, group=membership["group"], defaults={"role": membership["role"]})
        return Response(team_detail(user.profile))

    @transaction.atomic
    def delete(self, request, pk):
        user = get_object_or_404(get_user_model().objects.select_related("profile"), pk=pk)
        if user.pk == request.user.pk:
            raise PermissionDenied("Você não pode excluir a própria conta neste painel.")
        if (user.is_superuser or user.profile.community_role == "developer") and not is_developer(request.user):
            raise PermissionDenied("Esta conta é administrada pelo(a) Desenvolvedor(a).")
        # Newsletter delivery history stays available, but this account stops receiving mail.
        from apps.communications.models import NewsletterPreference
        NewsletterPreference.objects.filter(user=user).update(opted_in=False)
        user.delete()
        return Response(status=204)
