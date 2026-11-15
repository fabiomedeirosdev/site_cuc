from django.conf import settings
from django.db import models


class EditorialGroup(models.Model):
    class Cover(models.TextChoices):
        BIBLE = "bible", "Bíblia"
        HEART = "heart", "Coração entre mãos"
        PRAYER = "prayer", "Mãos em oração"
        FAMILY = "family", "Família"
        HEADQUARTERS = "headquarters", "Sede da comunidade"

    name = models.CharField("nome", max_length=120)
    slug = models.SlugField("endereço", max_length=140, unique=True)
    description = models.TextField("descrição", max_length=4000)
    address = models.CharField("endereço público", max_length=500, blank=True)
    whatsapp = models.CharField("WhatsApp público", max_length=15, blank=True)
    video_url = models.URLField("vídeo de apresentação", max_length=1000, blank=True)
    cover = models.CharField("imagem", max_length=20, choices=Cover.choices, default=Cover.BIBLE)
    custom_cover = models.ImageField("foto própria", upload_to="group-covers/%Y/%m/", blank=True)
    cover_alt = models.CharField("descrição da foto", max_length=200, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    position = models.PositiveSmallIntegerField("ordem", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name", "pk"]
        verbose_name = "grupo temático"
        verbose_name_plural = "grupos temáticos"

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        COORDINATOR = "coordinator", "Coordenador"
        COLUMNIST = "columnist", "Facilitador"

    group = models.ForeignKey(EditorialGroup, on_delete=models.CASCADE, related_name="memberships", verbose_name="grupo")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="editorial_memberships", verbose_name="usuário")
    role = models.CharField("função", max_length=20, choices=Role.choices)
    is_public = models.BooleanField("exibir no grupo", default=False)
    biography = models.TextField("apresentação", max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="editorial_unique_member"),
            models.CheckConstraint(condition=models.Q(role__in=["coordinator", "columnist"]), name="editorial_valid_role"),
        ]
        verbose_name = "vínculo editorial"
        verbose_name_plural = "vínculos editoriais"

    def __str__(self):
        return f"{self.user} — {self.group} ({self.get_role_display()})"
