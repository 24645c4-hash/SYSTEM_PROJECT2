"""Appointment models for MediManage."""

from django.conf import settings
from django.db import models


class Appointment(models.Model):
    """A scheduled visit connecting one patient with one doctor."""

    REQUESTED = "REQUESTED"
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    WAITING = "WAITING"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    STATUS_CHOICES = (
        (REQUESTED, "Requested"),
        (SCHEDULED, "Scheduled"),
        (CONFIRMED, "Confirmed"),
        (WAITING, "Waiting"),
        (IN_CONSULTATION, "In consultation"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (NO_SHOW, "No show"),
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        "authentication.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
        null=True,
        blank=True,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=REQUESTED)
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments_created",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("scheduled_for",)
        indexes = [
            models.Index(fields=("scheduled_for", "status")),
            models.Index(fields=("doctor", "scheduled_for")),
            models.Index(fields=("patient", "scheduled_for")),
        ]

    def __str__(self):
        doctor_name = self.doctor or "pending doctor assignment"
        when = self.scheduled_for.strftime("%Y-%m-%d %H:%M") if self.scheduled_for else "pending scheduling"
        return f"{self.patient} with {doctor_name} on {when}"