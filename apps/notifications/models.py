"""Internal notification models for MediManage."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """An internal clinic notification delivered to a user."""

    APPOINTMENT = "APPOINTMENT"
    ACCOUNT = "ACCOUNT"
    FOLLOW_UP = "FOLLOW_UP"
    SYSTEM = "SYSTEM"
    TYPE_CHOICES = (
        (APPOINTMENT, "Appointment"),
        (ACCOUNT, "Account"),
        (FOLLOW_UP, "Follow-up"),
        (SYSTEM, "System"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=SYSTEM,
    )
    title = models.CharField(max_length=160)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("recipient", "is_read")),
            models.Index(fields=("patient", "created_at")),
        ]

    def __str__(self):
        return f"{self.title} for {self.recipient}"