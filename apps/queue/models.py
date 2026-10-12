"""Queue management models for MediManage."""

from django.conf import settings
from django.db import models

from apps.appointments.models import Appointment
from apps.patients.models import Patient


class QueueEntry(models.Model):
    """A check-in queue entry for a patient awaiting or in consultation."""

    WAITING = "WAITING"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = (
        (WAITING, "Waiting"),
        (IN_CONSULTATION, "In consultation"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="queue_entries",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        related_name="queue_entries",
        null=True,
        blank=True,
    )
    queue_number = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=WAITING)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queue_entries_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("queue_number", "created_at")
        indexes = [
            models.Index(fields=("status", "queue_number")),
            models.Index(fields=("patient", "status")),
        ]

    def __str__(self):
        return f"#{self.queue_number} - {self.patient.get_full_name()} ({self.status})"

    def save(self, *args, **kwargs):
        if self.queue_number == 0:
            last_waiting = (
                QueueEntry.objects.filter(
                    status__in=(self.WAITING, self.IN_CONSULTATION)
                ).aggregate(models.Max("queue_number"))["queue_number__max"]
                or 0
            )
            self.queue_number = last_waiting + 1
        super().save(*args, **kwargs)
