from django.utils import timezone
from rest_framework import serializers
from .models import Event, Notice, Campaign, NewsletterSettings
from .images import clean_communication_image, image_path


class StrictSerializer(serializers.ModelSerializer):
    def validate_subject(self, value):
        if "\r" in value or "\n" in value:
            raise serializers.ValidationError("O assunto deve ter uma única linha.")
        return value

    def to_internal_value(self, data):
        allowed = {name for name, field in self.fields.items() if not field.read_only}
        if not isinstance(data, dict) or set(data) - allowed:
            raise serializers.ValidationError({"detail": "Campos não permitidos."})
        return super().to_internal_value(data)


class EventSerializer(StrictSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "description", "starts_at", "ends_at", "location", "is_published", "is_cancelled", "is_members_only", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if end and start and end <= start:
            raise serializers.ValidationError({"ends_at": "O término deve ser posterior ao início."})
        return attrs


class PublicEventSerializer(EventSerializer):
    description = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ["is_locked"]

    def get_is_locked(self, obj):
        from apps.billing.access import has_access
        from .policies import can_manage
        if not obj.is_members_only:
            return False
        user = self.context["request"].user
        if "_event_members_access" not in self.context:
            self.context["_event_members_access"] = has_access(user) or can_manage(user, "events")
        return not self.context["_event_members_access"]

    def get_description(self, obj):
        return None if self.get_is_locked(obj) else obj.description

    def get_location(self, obj):
        return None if self.get_is_locked(obj) else obj.location


class ImageSerializer(StrictSerializer):
    image = serializers.FileField(write_only=True, required=False)
    image_url = serializers.SerializerMethodField()
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)
    is_members_only = serializers.BooleanField(required=False, default=False)

    def get_image_url(self, obj):
        return image_path(self.image_kind, obj)

    def validate_image(self, value):
        return clean_communication_image(value)

    def validate(self, attrs):
        if attrs.get("image") and attrs.get("remove_image"):
            raise serializers.ValidationError({"image": "Envie uma imagem ou marque a remoção da atual."})
        has_image = attrs.get("image") or (getattr(self.instance, "image", None) and not attrs.get("remove_image"))
        if has_image and not attrs.get("image_alt", getattr(self.instance, "image_alt", "")).strip():
            raise serializers.ValidationError({"image_alt": "Descreva a imagem para quem usa leitor de tela."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("remove_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_image", False):
            validated_data["image"] = ""
            validated_data["image_alt"] = ""
        return super().update(instance, validated_data)


IMAGE_FIELDS = ["image", "image_url", "image_alt", "remove_image", "is_members_only"]


class NoticeSerializer(ImageSerializer):
    image_kind = "notices"
    class Meta:
        model = Notice
        fields = ["id", "title", "body", "is_published", "updated_at"] + IMAGE_FIELDS
        read_only_fields = ["id", "updated_at"]


class PublicNoticeSerializer(NoticeSerializer):
    body = serializers.SerializerMethodField()
    image_alt = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta(NoticeSerializer.Meta):
        fields = NoticeSerializer.Meta.fields + ["is_locked"]

    def get_is_locked(self, obj):
        from apps.billing.access import has_access
        from .policies import can_manage
        if not obj.is_members_only:
            return False
        if "_notice_members_access" not in self.context:
            user = self.context["request"].user
            self.context["_notice_members_access"] = has_access(user) or can_manage(user, "notices")
        return not self.context["_notice_members_access"]

    def get_body(self, obj):
        return None if self.get_is_locked(obj) else obj.body

    def get_image_url(self, obj):
        return None if self.get_is_locked(obj) else super().get_image_url(obj)

    def get_image_alt(self, obj):
        return "" if self.get_is_locked(obj) else obj.image_alt


class CampaignSerializer(ImageSerializer):
    image_kind = "campaigns"
    sent_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ["id", "subject", "introduction", "status", "scheduled_at", "created_at", "sent_count", "pending_count", "error"] + IMAGE_FIELDS
        read_only_fields = ["id", "created_at", "sent_count", "pending_count", "error"]

    def get_sent_count(self, obj):
        return obj.deliveries.filter(status="sent").count()

    def get_pending_count(self, obj):
        return obj.deliveries.filter(status="pending").count()

    def validate_status(self, value):
        if value not in {"draft", "scheduled", "cancelled"}:
            raise serializers.ValidationError("O estado de envio é controlado pelo servidor.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        status = attrs.get("status", getattr(self.instance, "status", "draft"))
        at = attrs.get("scheduled_at", getattr(self.instance, "scheduled_at", None))
        if status == "scheduled" and (not at or at <= timezone.now()):
            raise serializers.ValidationError({"scheduled_at": "Escolha uma data futura para o envio."})
        return attrs


class NewsletterSettingsSerializer(ImageSerializer):
    image_kind = "weekly"
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    hour = serializers.IntegerField(min_value=0, max_value=23)

    class Meta:
        model = NewsletterSettings
        fields = ["weekly_enabled", "weekday", "hour", "subject", "introduction"] + IMAGE_FIELDS
