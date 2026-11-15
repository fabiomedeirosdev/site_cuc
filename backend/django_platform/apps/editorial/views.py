from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from uuid import uuid4
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from .models import EditorialGroup, Membership
from .policies import can_manage_group, is_editorial_admin, managed_groups
from .serializers import ColumnistSerializer, GroupSerializer, ManagedGroupSerializer, MembershipInputSerializer, MembershipSerializer


def groups_with_team():
    return EditorialGroup.objects.prefetch_related("memberships__user__profile")


class PublicGroupsView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = GroupSerializer
    queryset = groups_with_team().filter(is_active=True)


class PublicGroupView(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = GroupSerializer
    queryset = groups_with_team().filter(is_active=True)
    lookup_field = "slug"


class PublicColumnistsView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ColumnistSerializer
    queryset = Membership.objects.filter(role=Membership.Role.COLUMNIST, is_public=True, group__is_active=True, user__is_active=True).select_related("group", "user__profile").order_by("user__profile__position", "user_id", "pk")

    def list(self, request, *args, **kwargs):
        from apps.accounts.models import Profile
        from apps.accounts.images import avatar_url
        rows = [(member.user.profile.position, member.user_id, member.pk, ColumnistSerializer(member).data) for member in self.get_queryset()]
        general = Profile.objects.filter(community_role="columnist", user__is_active=True).exclude(user__editorial_memberships__group__is_active=True).select_related("user")
        from .policies import public_name
        for profile in general:
            rows.append((profile.position, profile.user_id, 0, {
                "display_name": public_name(profile.user), "role": "columnist", "biography": profile.biography,
                "avatar_url": avatar_url(profile), "profile_url": f"/perfis/{profile.public_id}",
                "group_name": "", "group_slug": "",
            }))
        ordered = [row[3] for row in sorted(rows, key=lambda row: row[:3])]
        return self.get_paginated_response(self.paginate_queryset(ordered))


class ManagedGroupsView(AccountAPIView):
    def get(self, request):
        return Response({
            "is_administrator": is_editorial_admin(request.user),
            "groups": ManagedGroupSerializer(managed_groups(request.user).prefetch_related("memberships__user__profile"), many=True).data,
        })


class MembershipsView(AccountAPIView):
    def get_group(self, request, slug, lock=False):
        queryset = EditorialGroup.objects.select_for_update() if lock else EditorialGroup.objects.all()
        # Fora do escopo, a resposta não revela a existência de um grupo privado.
        group = get_object_or_404(queryset.filter(pk__in=managed_groups(request.user).values("pk")), slug=slug)
        if not can_manage_group(request.user, group):
            raise PermissionDenied()
        return group

    def get(self, request, slug):
        group = self.get_group(request, slug)
        members = group.memberships.select_related("user__profile")
        return Response(MembershipSerializer(members, many=True).data)

    @transaction.atomic
    def post(self, request, slug):
        group = self.get_group(request, slug, lock=True)
        serializer = MembershipInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        role = data.get("role", Membership.Role.COLUMNIST)
        if role != Membership.Role.COLUMNIST and not is_editorial_admin(request.user):
            raise PermissionDenied("Somente o administrador pode atribuir coordenadores.")
        if not data.get("email"):
            raise ValidationError({"email": "Informe o e-mail de uma conta ativa já cadastrada."})
        email = data.pop("email").strip().lower()
        create_account = data.pop("create_account", False)
        display_name = data.pop("display_name", "")
        password = data.pop("password", "")
        User = get_user_model()
        if create_account:
            if not display_name.strip() or not password:
                raise ValidationError({"detail": "Informe o nome e uma senha inicial para criar o acesso."})
            user = User(username=uuid4().hex, email=email)
            try:
                validate_password(password, user)
            except DjangoValidationError as error:
                raise ValidationError({"password": error.messages})
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError({"email": "Não foi possível criar o acesso. Confira o e-mail ou use uma conta já cadastrada."})
            user.set_password(password)
            try:
                with transaction.atomic():
                    user.save()
                    user.profile.display_name = display_name
                    user.profile.save(update_fields=["display_name"])
            except IntegrityError:
                raise ValidationError({"email": "Não foi possível criar o acesso. Confira o e-mail ou use uma conta já cadastrada."})
        else:
            if password or display_name:
                raise ValidationError({"detail": "Use a opção de criar acesso para definir nome e senha."})
            user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise ValidationError({"email": "Não foi possível vincular essa conta. Confira o e-mail e o cadastro com a administração."})
        if group.memberships.filter(user=user).exists():
            raise ValidationError({"email": "Esta conta já possui vínculo neste grupo."})
        member = Membership.objects.create(group=group, user=user, **{**data, "role": role})
        return Response(MembershipSerializer(member).data, status=201)


class MembershipDetailView(MembershipsView):
    http_method_names = ["patch", "delete", "options"]

    def get_member(self, request, slug, pk):
        group = self.get_group(request, slug, lock=True)
        member = get_object_or_404(group.memberships.select_related("user__profile"), pk=pk)
        if member.role == Membership.Role.COORDINATOR and not is_editorial_admin(request.user):
            raise PermissionDenied("Somente o administrador pode alterar vínculos de coordenadores.")
        return member

    @transaction.atomic
    def patch(self, request, slug, pk):
        member = self.get_member(request, slug, pk)
        serializer = MembershipInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "email" in data:
            raise ValidationError({"email": "A conta de um vínculo não pode ser substituída."})
        if set(data) & {"create_account", "password", "display_name"}:
            # O padrão do serializer não deve transformar um PATCH em criação de conta.
            if data.get("create_account") or "password" in data or "display_name" in data:
                raise ValidationError({"detail": "Nome e senha de acesso são definidos no cadastro, não no vínculo."})
            data.pop("create_account", None)
        if data.get("role", member.role) != Membership.Role.COLUMNIST and not is_editorial_admin(request.user):
            raise PermissionDenied("Somente o administrador pode atribuir coordenadores.")
        for field, value in data.items():
            setattr(member, field, value)
        member.save()
        return Response(MembershipSerializer(member).data)

    @transaction.atomic
    def delete(self, request, slug, pk):
        member = self.get_member(request, slug, pk)
        member.delete()
        return Response(status=204)
