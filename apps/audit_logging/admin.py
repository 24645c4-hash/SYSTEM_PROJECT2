"""Admin configuration for protected audit logs."""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "content_type", "object_id")
    list_filter = ("action", "content_type", "created_at")
    search_fields = ("user__username", "action", "description", "object_id")
    readonly_fields = (
        "user",
        "action",
        "description",
        "content_type",
        "object_id",
        "ip_address",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False