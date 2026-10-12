"""Forms for medical records and clinical notes."""

from django import forms

from .models import Consultation, MedicalRecord, Prescription


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            "blood_type",
            "allergies",
            "chronic_conditions",
            "surgical_history",
            "family_history",
            "notes",
        ]
        widgets = {
            "blood_type": forms.Select(attrs={"class": "form-control"}, choices=MedicalRecord.BLOOD_TYPE_CHOICES),
            "allergies": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "chronic_conditions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "surgical_history": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "family_history": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            "chief_complaint",
            "diagnosis",
            "treatment",
            "clinical_notes",
            "follow_up_date",
        ]
        widgets = {
            "chief_complaint": forms.TextInput(attrs={"class": "form-control"}),
            "diagnosis": forms.TextInput(attrs={"class": "form-control"}),
            "treatment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "clinical_notes": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "follow_up_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = [
            "medication",
            "dosage",
            "instructions",
            "prescription_date",
            "duration_days",
            "quantity",
            "refills",
        ]
        widgets = {
            "medication": forms.TextInput(attrs={"class": "form-control"}),
            "dosage": forms.TextInput(attrs={"class": "form-control"}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "prescription_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "duration_days": forms.NumberInput(attrs={"class": "form-control"}),
            "quantity": forms.TextInput(attrs={"class": "form-control"}),
            "refills": forms.NumberInput(attrs={"class": "form-control"}),
        }
