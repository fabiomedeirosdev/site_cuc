from django.contrib import admin

from .models import EditorialGroup, Membership
from .forms import EditorialGroupForm


class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


@admin.register(EditorialGroup)
class EditorialGroupAdmin(SuperuserOnlyAdmin):
    form = EditorialGroupForm
    list_display = ["name", "slug", "is_active", "position"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Membership)
class MembershipAdmin(SuperuserOnlyAdmin):
    list_display = ["user", "group", "role", "is_public"]
    list_filter = ["group", "role", "is_public"]
    autocomplete_fields = ["user", "group"]
    search_fields = ["user__email", "group__name"]
