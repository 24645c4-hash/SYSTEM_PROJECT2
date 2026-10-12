"""Forms for the queue management application."""

from django import forms

from apps.appointments.models import Appointment
from apps.patients.models import Patient

from .models import QueueEntry


class QueueEntryForm(forms.ModelForm):
    class Meta:
        model = QueueEntry
        fields = ("patient", "appointment", "status", "notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(status=Patient.ACTIVE)
        self.fields["appointment"].queryset = Appointment.objects.select_related(
            "patient",
            "doctor__staff_profile__user",
        )

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get("patient")
        appointment = cleaned_data.get("appointment")

        if patient and appointment and appointment.patient_id != patient.pk:
            raise forms.ValidationError(
                "The selected appointment must belong to the chosen patient."
            )

        return cleaned_data


class QueueStatusForm(forms.ModelForm):
    class Meta:
        model = QueueEntry
        fields = ("status", "notes")
