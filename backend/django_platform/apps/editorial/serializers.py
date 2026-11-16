from rest_framework import serializers

from apps.core.media import public_image_url
from .models import EditorialGroup, Membership
from .policies import public_name


class PublicMemberSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["display_name", "role", "biography", "avatar_url", "profile_url"]

    def get_display_name(self, obj):
        return public_name(obj.user)

    def get_avatar_url(self, obj):
        from apps.accounts.images import avatar_url
        return avatar_url(obj.user.profile)

    def get_profile_url(self, obj):
        return f"/perfis/{obj.user.profile.public_id}"


class GroupSerializer(serializers.ModelSerializer):
    video_embed_url = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = EditorialGroup
        fields = ["id", "name", "slug", "description", "cover", "cover_url", "cover_alt", "team", "address", "whatsapp", "video_embed_url"]

    def get_cover_url(self, obj):
        return public_image_url(obj.custom_cover)

    def get_video_embed_url(self, obj):
        from apps.content.video import embed_url
        return embed_url(obj.video_url)

    def get_team(self, obj):
        members = [m for m in obj.memberships.all() if m.is_public and m.user.is_active]
        members.sort(key=lambda m: (m.user.profile.position, m.user_id, m.pk))
        return PublicMemberSerializer(members, many=True).data


class ManagedGroupSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ["is_active"]


class ColumnistSerializer(PublicMemberSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    group_slug = serializers.CharField(source="group.slug", read_only=True)

    class Meta(PublicMemberSerializer.Meta):
        fields = PublicMemberSerializer.Meta.fields + ["group_name", "group_slug"]


class MembershipSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "display_name", "role", "biography", "is_public"]

    def get_display_name(self, obj):
        return public_name(obj.user)


class MembershipInputSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254, required=False)
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    biography = serializers.CharField(max_length=2000, allow_blank=True, required=False)
    is_public = serializers.BooleanField(required=False)
    create_account = serializers.BooleanField(required=False, default=False, write_only=True)
    display_name = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(max_length=1024, required=False, write_only=True, trim_whitespace=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"detail": "Informe somente e-mail, função, apresentação e visibilidade."})
        return super().to_internal_value(data)
