import uuid

from django.conf import settings
from django.db import models


class CoverImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to="covers/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "foto de capa"
        verbose_name_plural = "fotos de capa"


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicado"

    class Audience(models.TextChoices):
        PUBLIC = "public", "Público"
        MEMBERS = "members", "Exclusivo para assinantes"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    group = models.ForeignKey("editorial.EditorialGroup", on_delete=models.PROTECT, related_name="articles")
    title = models.CharField("título", max_length=200)
    excerpt = models.CharField("resumo", max_length=500, blank=True)
    body = models.TextField("texto", max_length=200000, blank=True)
    cover = models.ForeignKey(CoverImage, on_delete=models.SET_NULL, null=True, blank=True)
    cover_alt = models.CharField("descrição da foto", max_length=200, blank=True)
    video_url = models.URLField("link do YouTube", max_length=1000, blank=True)
    status = models.CharField("situação", max_length=12, choices=Status.choices, default=Status.DRAFT)
    audience = models.CharField("visibilidade", max_length=12, choices=Audience.choices, default=Audience.PUBLIC)
    published_at = models.DateTimeField("publicado em", null=True, blank=True)
    is_featured = models.BooleanField("destaque na página inicial", default=False)
    featured_position = models.PositiveSmallIntegerField("ordem do destaque", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-pk"]
        verbose_name = "conteúdo"
        verbose_name_plural = "conteúdos"
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=["draft", "published"]), name="content_valid_status"),
            models.CheckConstraint(condition=models.Q(audience__in=["public", "members"]), name="content_valid_audience"),
        ]

    def __str__(self):
        return self.title
