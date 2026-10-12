"""Admin configuration for staff and doctor profiles."""

from django.contrib import admin

from .models import DoctorProfile, StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "employee_id", "department", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name", "employee_id")


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("staff_profile", "specialization", "license_number")
    search_fields = (
        "staff_profile__user__first_name",
        "staff_profile__user__last_name",
        "specialization",
        "license_number",
    )