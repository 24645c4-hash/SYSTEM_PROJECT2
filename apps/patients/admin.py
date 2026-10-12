"""Admin configuration for patient profiles."""

from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "medical_record_number",
        "get_full_name",
        "date_of_birth",
        "phone",
        "status",
        "user",
    )
    list_filter = ("status", "gender")
    search_fields = (
        "medical_record_number",
        "first_name",
        "middle_name",
        "last_name",
        "phone",
        "email",
    )
    readonly_fields = ("medical_record_number", "created_at", "updated_at")