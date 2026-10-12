"""Forms for the appointments application."""

from django import forms

from apps.authentication.models import DoctorProfile
from apps.patients.models import Patient

from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = (
            "patient",
            "doctor",
            "scheduled_for",
            "status",
            "reason",
            "notes",
        )
        widgets = {
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(status=Patient.ACTIVE)
        self.fields["doctor"].queryset = DoctorProfile.objects.select_related(
            "staff_profile__user"
        )


class PatientAppointmentRequestForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("reason", "notes")
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("doctor", "scheduled_for", "status", "notes")
        widgets = {
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = DoctorProfile.objects.select_related(
            "staff_profile__user"
        )
        self.fields["doctor"].required = False
        self.fields["scheduled_for"].required = False
