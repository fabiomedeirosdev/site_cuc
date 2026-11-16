from django.apps import AppConfig


class WebPushConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.webpush"
    verbose_name = "Notificações do aplicativo"

    def ready(self):
        from . import signals  # noqa: F401
