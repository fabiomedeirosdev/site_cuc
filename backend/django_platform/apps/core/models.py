from django.conf import settings
from django.db import models


class InboxMailbox(models.Model):
    key = models.CharField(max_length=64, unique=True)
    uid_validity = models.CharField(max_length=40, blank=True)
    last_uid = models.PositiveBigIntegerField(default=0)


class IncomingMessage(models.Model):
    source_key = models.CharField(max_length=140, unique=True)
    sender = models.EmailField(blank=True)
    subject = models.CharField(max_length=300)
    body = models.TextField(max_length=30000, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-received_at", "-pk"]


DEFAULT_FOUNDERS_STORY = "Eneida Carmona e Luiz Carmona são psicólogos e fundadores da Comunidade Unidos em Cristo. A missão nasceu de encontros de oração entre casais amigos, com o desejo de partilhar a Palavra de Deus e viver a fé de forma concreta. Com o tempo, passou a oferecer formações, palestras e projetos de restauração do ser."


class FoundersPage(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    title = models.CharField("título da página", max_length=200, default="Nossos fundadores")
    body = models.TextField("história dos fundadores", max_length=50000, default=DEFAULT_FOUNDERS_STORY)
    photo = models.ImageField("foto dos fundadores", upload_to="institutional/founders/%Y/%m/", blank=True)
    photo_alt = models.CharField("descrição da foto", max_length=200, default="Fundadores da Comunidade Unidos em Cristo")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "página dos fundadores"
        verbose_name_plural = "página dos fundadores"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="core_single_founders_page")]
