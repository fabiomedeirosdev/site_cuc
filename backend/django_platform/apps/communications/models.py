import uuid
from django.conf import settings
from django.db import models
from .images import communication_image_storage


class Delegation(models.Model):
    coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="communications_delegation")
    facilitator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="communications_delegations")
    can_edit_agenda = models.BooleanField(default=True)
    can_edit_mural = models.BooleanField(default=True)
    can_edit_newsletter = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["coordinator", "facilitator"], name="communications_unique_delegate")]


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=20000)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300)
    is_published = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_members_only = models.BooleanField("apenas para assinantes", default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "pk"]


class Notice(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=20000)
    is_published = models.BooleanField(default=False)
    is_members_only = models.BooleanField("apenas para assinantes", default=False)
    image = models.ImageField("imagem de divulgação", storage=communication_image_storage, upload_to="notices/%Y/%m/", blank=True)
    image_alt = models.CharField("descrição da imagem", max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]


class NewsletterPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="newsletter_preference")
    email = models.EmailField(unique=True)
    opted_in = models.BooleanField(default=False)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    confirmation_hash = models.CharField(max_length=64, blank=True)
    confirmation_expires_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.email and self.user_id:
            self.email = self.user.email
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class NewsletterSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    weekly_enabled = models.BooleanField(default=False)
    weekday = models.PositiveSmallIntegerField(default=0)
    hour = models.PositiveSmallIntegerField(default=9)
    subject = models.CharField(max_length=180, default="Sua semana na Comunidade Unidos em Cristo")
    introduction = models.TextField(max_length=10000, default="Uma nova semana para caminhar juntos na fé. Confira os encontros e as novidades da comunidade.")
    is_members_only = models.BooleanField("apenas para assinantes", default=False)
    image = models.ImageField("imagem da newsletter", storage=communication_image_storage, upload_to="newsletters/%Y/%m/", blank=True)
    image_alt = models.CharField("descrição da imagem", max_length=200, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)


class Campaign(models.Model):
    subject = models.CharField(max_length=180)
    introduction = models.TextField(max_length=10000)
    is_members_only = models.BooleanField("apenas para assinantes", default=False)
    image = models.ImageField("imagem da newsletter", storage=communication_image_storage, upload_to="newsletters/%Y/%m/", blank=True)
    image_alt = models.CharField("descrição da imagem", max_length=200, blank=True)
    status = models.CharField(max_length=20, default="draft", choices=[("draft", "Rascunho"), ("scheduled", "Agendado"), ("sending", "Em envio"), ("sent", "Concluído"), ("cancelled", "Envio cancelado")])
    scheduled_at = models.DateTimeField(null=True, blank=True)
    weekly_key = models.CharField(max_length=20, null=True, unique=True, editable=False)
    snapshot = models.JSONField(default=dict, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    error = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class Delivery(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="deliveries")
    preference = models.ForeignKey(NewsletterPreference, on_delete=models.PROTECT)
    email = models.EmailField()
    status = models.CharField(max_length=15, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["campaign", "preference"], name="communications_unique_delivery")]
