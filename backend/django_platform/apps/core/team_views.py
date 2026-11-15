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
from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import public_name
from .management_views import AdminView, paginate


class TeamInput(serializers.Serializer):
    email = serializers.EmailField(required=False)
    display_name = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(max_length=1024, required=False, write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=["", "founder", "developer", "columnist", "coordinator"], required=False)
    group = serializers.PrimaryKeyRelatedField(queryset=EditorialGroup.objects.all(), allow_null=True, required=False)
    position = serializers.IntegerField(min_value=0, max_value=32767, required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError("Campos não permitidos.")
        return super().to_internal_value(data)


def team_row(profile):
    return {"id": profile.user_id, "display_name": public_name(profile.user), "email": profile.user.email,
            "role": profile_role(profile.user)[0], "community_role": profile.community_role, "position": profile.position}


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class TeamView(AdminView):
    def get(self, request):
        profiles = Profile.objects.select_related("user").order_by("position", "pk")
        query = request.query_params.get("q", "").strip()[:150]
        if query:
            profiles = profiles.filter(Q(display_name__icontains=query) | Q(user__email__icontains=query))
        return paginate(request, profiles, team_row)

    def validate_input(self, request, partial=False):
        form = TeamInput(data=request.data, partial=partial)
        form.is_valid(raise_exception=True)
        values = form.validated_data
        if "position" in values and not is_developer(request.user):
            raise PermissionDenied("Somente o Desenvolvedor pode alterar a ordem dos membros.")
        if values.get("role") == "developer" and not is_developer(request.user):
            raise PermissionDenied("Somente o Desenvolvedor pode atribuir essa função.")
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
            raise PermissionDenied("Esta conta é administrada pelo Desenvolvedor.")
        group = values.get("group")
        role = values.get("role")
        if group and not role:
            raise ValidationError({"role": "Selecione uma função para o vínculo com o grupo."})
        if role == "coordinator" and not group:
            raise ValidationError({"group": "Coordenadores mantêm o vínculo obrigatório com um grupo."})
        if role == "coordinator" and profile.community_role:
            raise ValidationError({"role": "Remova a função geral antes de atribuir a coordenação."})
        if role in {"founder", "developer", "columnist", ""}:
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
        if set(request.data) - {"role", "position"}:
            raise ValidationError("Edite somente a função geral e a ordem.")
        user = get_object_or_404(get_user_model().objects.select_related("profile"), pk=pk)
        self.assign(request, user, self.validate_input(request, partial=True))
        return Response(team_row(user.profile))
