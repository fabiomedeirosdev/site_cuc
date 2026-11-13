from django.contrib import admin

from apps.editorial.admin import SuperuserOnlyAdmin
from .models import ConsumerRequest, EmailJob, PaidPeriod, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(SuperuserOnlyAdmin):
    list_display = ["email", "status", "paid_until", "safety_hold", "updated_at"]
    search_fields = ["email", "provider_id"]
    list_filter = ["status", "safety_hold"]
    readonly_fields = ["provider_id", "checkout", "user", "email", "status", "paid_until", "provider_updated_at", "cancel_requested_at", "canceled_at", "created_at", "updated_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConsumerRequest)
class ConsumerRequestAdmin(SuperuserOnlyAdmin):
    list_display = ["id", "subscription", "kind", "created_at", "resolved_at"]
    readonly_fields = ["id", "subscription", "kind", "message", "created_at"]
    list_filter = ["kind", "resolved_at"]

    def has_add_permission(self, request):
        return False


@admin.register(EmailJob)
class EmailJobAdmin(SuperuserOnlyAdmin):
    list_display = ["subscription", "kind", "sent_at", "last_error"]
    readonly_fields = ["subscription", "kind", "deduplication_key", "sent_at", "attempts", "last_error", "created_at"]

    def has_add_permission(self, request):
        return False
