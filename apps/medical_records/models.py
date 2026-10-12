"""Medical record, consultation, and prescription models."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class MedicalRecord(models.Model):
    """The longitudinal clinical summary for one patient."""

    BLOOD_TYPE_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
        ("Unknown", "Unknown"),
    ]

    patient = models.OneToOneField(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_record",
    )
    blood_type = models.CharField(max_length=8, blank=True, choices=BLOOD_TYPE_CHOICES)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    surgical_history = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Medical record for {self.patient}"


class Consultation(models.Model):
    """A doctor's clinical encounter with a patient."""

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="consultations",
    )
    doctor = models.ForeignKey(
        "authentication.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="consultations",
    )
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation",
    )
    consultation_date = models.DateTimeField(default=timezone.now)
    chief_complaint = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-consultation_date",)
        indexes = [
            models.Index(fields=("patient", "-consultation_date")),
            models.Index(fields=("doctor", "-consultation_date")),
        ]

    def __str__(self):
        return f"Consultation for {self.patient} on {self.consultation_date:%Y-%m-%d}"


class Prescription(models.Model):
    """Medication instructions associated with a consultation."""

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    doctor = models.ForeignKey(
        "authentication.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="prescriptions",
    )
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
    )
    medication = models.CharField(max_length=160)
    dosage = models.CharField(max_length=120)
    instructions = models.TextField()
    prescription_date = models.DateField(default=timezone.localdate)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.CharField(max_length=80, blank=True)
    refills = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-prescription_date", "-created_at")

    def __str__(self):
        return f"{self.medication} for {self.patient}"