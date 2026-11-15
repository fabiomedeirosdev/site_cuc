from django.conf import settings
from django.db import models
import uuid
from .images import profile_image_storage


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    community_role = models.CharField("função geral", max_length=20, blank=True, choices=[("founder", "Fundador"), ("developer", "Desenvolvedor"), ("columnist", "Facilitador")])
    position = models.PositiveSmallIntegerField("ordem de exibição", default=0)
    display_name = models.CharField("nome de exibição", max_length=150, blank=True)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    avatar = models.ImageField("foto de perfil", storage=profile_image_storage, upload_to="avatars/%Y/%m/", blank=True)
    biography = models.TextField("biografia", max_length=3000, blank=True)
    website = models.URLField("site", max_length=500, blank=True)
    phone = models.CharField("telefone público", max_length=30, blank=True)
    video_url = models.URLField("vídeo de apresentação no YouTube", max_length=1000, blank=True)
    pending_email = models.EmailField("novo e-mail pendente", max_length=254, blank=True)
    email_change_hash = models.CharField(max_length=64, blank=True)
    email_change_auth_hash = models.CharField(max_length=64, blank=True)
    email_change_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"
        permissions = [
            ("read_articles", "Pode ler artigos publicados"),
            ("watch_videos", "Pode assistir a vídeos publicados"),
            ("listen_audio", "Pode ouvir áudios publicados"),
        ]

    def __str__(self):
        return self.display_name or self.user.email or str(self.user_id)
