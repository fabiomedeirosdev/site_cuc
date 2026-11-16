from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers

from apps.editorial.models import EditorialGroup
from apps.editorial.policies import is_editorial_admin, public_name
from apps.core.media import public_image_url
from .models import Article, CoverImage
from .policies import author_groups
from .video import embed_url, video_id


class ArticleSummarySerializer(serializers.ModelSerializer):
    excerpt = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    author_profile_url = serializers.SerializerMethodField()
    group_name = serializers.CharField(source="group.name", read_only=True)
    cover_url = serializers.SerializerMethodField()
    has_video = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "excerpt", "author_name", "author_profile_url", "group_name", "cover_url", "cover_alt", "published_at", "updated_at", "has_video", "is_locked", "is_featured", "featured_position"]

    def get_excerpt(self, obj):
        return "" if self.get_is_locked(obj) else obj.excerpt

    def get_author_name(self, obj):
        return public_name(obj.author)

    def get_author_profile_url(self, obj):
        return f"/perfis/{obj.author.profile.public_id}"

    def get_cover_url(self, obj):
        return public_image_url(obj.cover.file) if obj.cover else None

    def get_has_video(self, obj):
        return bool(obj.video_url)

    def get_is_locked(self, obj):
        from apps.billing.access import has_access
        request = self.context.get("request")
        return obj.audience == Article.Audience.MEMBERS and not (request and (has_access(request.user) or is_editorial_admin(request.user)))


class ArticleReadSerializer(ArticleSummarySerializer):
    body = serializers.SerializerMethodField()
    video_embed_url = serializers.SerializerMethodField()

    class Meta(ArticleSummarySerializer.Meta):
        fields = ArticleSummarySerializer.Meta.fields + ["body", "video_embed_url"]

    def get_body(self, obj):
        return None if self.get_is_locked(obj) else obj.body

    def get_video_embed_url(self, obj):
        return None if self.get_is_locked(obj) else embed_url(obj.video_url)


class ArticleEditorSerializer(ArticleSummarySerializer):
    excerpt = serializers.CharField(read_only=True)
    class Meta(ArticleSummarySerializer.Meta):
        fields = ArticleSummarySerializer.Meta.fields + ["group", "cover", "body", "video_url", "status", "audience"]


class ArticleWriteSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=EditorialGroup.objects.none())
    cover = serializers.PrimaryKeyRelatedField(queryset=CoverImage.objects.none(), allow_null=True, required=False)

    class Meta:
        model = Article
        fields = ["title", "excerpt", "body", "group", "cover", "cover_alt", "video_url", "status", "audience"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        self.fields["group"].queryset = author_groups(user)
        self.fields["cover"].queryset = CoverImage.objects.all() if is_editorial_admin(user) else CoverImage.objects.filter(owner=user)
        if self.instance and not is_editorial_admin(user):
            # A capa atual pode ter sido enviada pelo coordenador durante uma revisão.
            self.fields["cover"].queryset = CoverImage.objects.filter(Q(owner=user) | Q(pk=self.instance.cover_id))
            # Revisar uma publicação não autoriza transferi-la para um grupo de outro autor.
            self.fields["group"].queryset = author_groups(user).filter(Q(pk__in=author_groups(self.instance.author).values("pk")) | Q(pk=self.instance.group_id))

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"detail": "O conteúdo contém campos não permitidos."})
        return super().to_internal_value(data)

    def validate_video_url(self, value):
        identifier = video_id(value)
        return f"https://www.youtube.com/watch?v={identifier}" if identifier else ""

    def validate(self, attrs):
        def value(field, default=""):
            return attrs.get(field, getattr(self.instance, field, default))
        if not value("body").strip() and not value("video_url"):
            raise serializers.ValidationError({"body": "Escreva um texto ou informe um vídeo."})
        if value("status", "draft") == "published":
            if not value("cover", None):
                raise serializers.ValidationError({"cover": "Adicione uma foto de capa antes de publicar."})
            if not value("cover_alt").strip():
                raise serializers.ValidationError({"cover_alt": "Descreva a imagem de capa antes de publicar."})
        return attrs

    def save(self, **kwargs):
        if self.validated_data.get("status", getattr(self.instance, "status", "draft")) == "published" and not getattr(self.instance, "published_at", None):
            kwargs["published_at"] = timezone.now()
        return super().save(**kwargs)
