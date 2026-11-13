from django.contrib import admin
from apps.editorial.admin import SuperuserOnlyAdmin
from .models import Event, Notice, Campaign, NewsletterPreference, Delegation


@admin.register(Event, Notice, Campaign, NewsletterPreference, Delegation)
class CommunicationsAdmin(SuperuserOnlyAdmin):
    # A interface de coordenação usa as APIs que validam os vínculos. O Admin
    # técnico permite consulta, sem contornar envio, consentimento ou delegação.
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
