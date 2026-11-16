from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .forms import AccountChangeForm, AccountCreationForm, EmailAdminAuthenticationForm
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ["display_name", "community_role", "position"]

    def get_readonly_fields(self, request, obj=None):
        from .policies import is_application_admin
        return [] if is_application_admin(request.user) else ["community_role", "position"]


class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    inlines = [ProfileInline]
    readonly_fields = ["username", "last_login", "date_joined"]
    add_fieldsets = [(None, {"classes": ["wide"], "fields": ["email", "first_name", "last_name", "password1", "password2"]})]
    list_display = ["email", "first_name", "last_name", "is_active", "is_staff"]
    ordering = ["email"]


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), AccountAdmin)
admin.site.login_form = EmailAdminAuthenticationForm
admin.site.site_header = "Comunidade Unidos em Cristo"
admin.site.site_title = "Administração CUC"
admin.site.index_title = "Gestão da comunidade"
admin.site.site_url = settings.PUBLIC_FRONTEND_URL + "/painel"
