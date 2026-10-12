"""Admin configuration for appointments."""

from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "scheduled_for", "status", "created_by")
    list_filter = ("status", "scheduled_for")
    search_fields = (
        "patient__medical_record_number",
        "patient__first_name",
        "patient__last_name",
        "doctor__staff_profile__user__last_name",
    )
    date_hierarchy = "scheduled_for"