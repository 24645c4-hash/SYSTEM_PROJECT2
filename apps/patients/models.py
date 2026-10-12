"""Patient profile models for MediManage."""

import uuid

from django.conf import settings
from django.db import models


def generate_medical_record_number():
    return f"MM-{uuid.uuid4().hex[:12].upper()}"


class Patient(models.Model):
    """A clinic-verified patient profile, optionally linked to a user account."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    STATUS_CHOICES = (
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (ARCHIVED, "Archived"),
    )

    MALE = "MALE"
    FEMALE = "FEMALE"
    GENDER_CHOICES = (
        (MALE, "Male"),
        (FEMALE, "Female"),
    )

    medical_record_number = models.CharField(
        max_length=32,
        unique=True,
        default=generate_medical_record_number,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_profile",
    )
    first_name = models.CharField(max_length=120)
    middle_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=24, choices=GENDER_CHOICES, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [
            models.Index(fields=("last_name", "first_name")),
            models.Index(fields=("status",)),
            models.Index(fields=("phone",)),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.medical_record_number})"

    def get_full_name(self):
        return " ".join(part for part in (self.first_name, self.middle_name, self.last_name) if part)