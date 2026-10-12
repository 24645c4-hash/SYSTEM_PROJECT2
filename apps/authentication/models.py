"""Staff and doctor profile models for MediManage."""

from django.conf import settings
from django.db import models

from .roles import ADMIN, DOCTOR, RECEPTIONIST


class StaffProfile(models.Model):
    """Administrative profile for a clinic staff account."""

    ROLE_CHOICES = (
        (ADMIN, "Administrator"),
        (RECEPTIONIST, "Receptionist"),
        (DOCTOR, "Doctor"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    employee_id = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class DoctorProfile(models.Model):
    """Clinical profile linked to a staff member with the doctor role."""

    staff_profile = models.OneToOneField(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    specialization = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    availability_notes = models.TextField(blank=True)

    def __str__(self):
        name = self.staff_profile.user.get_full_name() or self.staff_profile.user.username
        return f"Dr. {name}"