from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from urllib.parse import urlparse
import re

from .models import Profile
from .policies import account_roles, can_publish_phone, consumption_capabilities, profile_role, is_developer
from .images import avatar_url, clean_avatar
from apps.content.video import video_id, embed_url


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    avatar = serializers.FileField(required=False, write_only=True)
    remove_avatar = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = Profile
        fields = ["display_name", "biography", "website", "phone", "video_url", "avatar", "remove_avatar"]

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"detail": "Informe somente os campos editáveis do seu perfil."})
        return super().to_internal_value(data)

    def validate_avatar(self, value):
        return clean_avatar(value)

    def validate_website(self, value):
        if value:
            url = urlparse(value)
            if url.scheme not in {"https", "http"} or url.username or url.password:
                raise serializers.ValidationError("Use um endereço de site HTTP ou HTTPS, sem credenciais.")
        return value

    def validate_video_url(self, value):
        identifier = video_id(value)
        return f"https://www.youtube.com/watch?v={identifier}" if identifier else ""

    def validate_phone(self, value):
        if not can_publish_phone(self.instance.user):
            raise PermissionDenied("Somente o desenvolvedor e os coordenadores podem publicar telefone de contato.")
        if value and (not re.fullmatch(r"\+?[0-9() .-]+", value) or not 8 <= len(re.sub(r"\D", "", value)) <= 15):
            raise serializers.ValidationError("Informe um telefone válido, com DDD e, se necessário, código do país.")
        return value

    def validate(self, attrs):
        if attrs.get("avatar") and attrs.get("remove_avatar"):
            raise serializers.ValidationError({"avatar": "Envie uma foto ou marque a remoção da atual."})
        return attrs

    def update(self, instance, validated_data):
        if validated_data.pop("remove_avatar", False):
            validated_data["avatar"] = ""
        return super().update(instance, validated_data)


class PublicProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    video_embed_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["public_id", "display_name", "avatar_url", "role", "role_label", "biography", "website", "phone", "video_embed_url"]

    def get_display_name(self, obj):
        from apps.editorial.policies import public_name
        return public_name(obj.user)

    def get_avatar_url(self, obj):
        return avatar_url(obj)

    def get_role(self, obj):
        return profile_role(obj.user)[0]

    def get_role_label(self, obj):
        return profile_role(obj.user)[1]

    def get_phone(self, obj):
        return obj.phone if can_publish_phone(obj.user) else ""

    def get_video_embed_url(self, obj):
        return embed_url(obj.video_url)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "A senha atual está incorreta."})
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "Escolha uma senha diferente da atual."})
        try:
            password_validation.validate_password(attrs["new_password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": error.messages})
        return attrs


def account_data(user):
    from apps.editorial.models import Membership
    from apps.editorial.policies import can_create_groups, managed_groups
    from apps.billing.access import account_subscription
    from apps.communications.policies import can_manage, can_delegate

    profile, _ = Profile.objects.get_or_create(user=user)
    subscription = account_subscription(user)
    return {
        "id": user.pk,
        "email": user.email,
        "display_name": profile.display_name or user.get_full_name(),
        "public_id": str(profile.public_id),
        "public_profile_url": f"/perfis/{profile.public_id}",
        "avatar_url": avatar_url(profile),
        "biography": profile.biography,
        "website": profile.website,
        "phone": profile.phone if can_publish_phone(user) else "",
        "video_url": profile.video_url,
        "profile_role": profile_role(user)[0],
        "profile_role_label": profile_role(user)[1],
        "can_publish_phone": can_publish_phone(user),
        "pending_email": profile.pending_email,
        "email_change_available": email_change_available(),
        "roles": account_roles(user),
        "capabilities": consumption_capabilities(user),
        # Login e papel não comprovam pagamento nem liberam conteúdo exclusivo.
        "exclusive_content_access": subscription["has_access"],
        "subscription_status": subscription["status"],
        "subscription_access_until": subscription["access_until"],
        "can_manage_editorial_groups": managed_groups(user).exists(),
        "can_create_groups": can_create_groups(user),
        "can_access_panel": bool(user.is_active and (user.is_superuser or user.editorial_memberships.filter(group__is_active=True).exists() or can_manage(user))),
        "can_manage_communications": can_manage(user),
        "can_delegate_communications": can_delegate(user),
        "communication_sections": [kind for kind in ["events", "notices", "campaigns"] if can_manage(user, kind)],
        "can_order_members": is_developer(user),
        "editorial_groups": list(Membership.objects.filter(user=user, group__is_active=True).values("group__name", "group__slug", "role")),
    }


def email_change_available():
    from django.conf import settings
    return bool(settings.EMAIL_HOST and settings.DEFAULT_FROM_EMAIL and not settings.DEFAULT_FROM_EMAIL.endswith(".invalid"))


class EmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField(max_length=254)
    current_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != set(self.fields):
            raise serializers.ValidationError({"detail": "Informe o novo e-mail e a senha atual."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        from django.contrib.auth import get_user_model
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "A senha atual está incorreta."})
        email = attrs["new_email"].strip().lower()
        if email == user.email.strip().lower():
            raise serializers.ValidationError({"new_email": "Informe um endereço diferente do e-mail atual."})
        if get_user_model().objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError({"new_email": "Não foi possível usar este endereço. Confira o e-mail informado."})
        attrs["new_email"] = email
        return attrs
