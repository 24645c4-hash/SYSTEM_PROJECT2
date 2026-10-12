"""Forms for patient registration, profile management, and account activation."""

from django import forms

from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "status",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class PatientAccountActivationForm(forms.Form):
    """Validate that a patient is ready to receive a temporary credential."""

    def __init__(self, *args, patient: Patient, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient

    def clean(self):
        cleaned_data = super().clean()

        if self.patient.user_id:
            raise forms.ValidationError("This patient already has an account.")
        if self.patient.status != Patient.ACTIVE:
            raise forms.ValidationError(
                "Only active patient profiles can receive an account."
            )
        if not self.patient.email:
            raise forms.ValidationError(
                "Add an email address to the patient profile before creating an account."
            )

        return cleaned_data