"""Admin configuration for medical records and clinical documents."""

from django.contrib import admin

from .models import Consultation, MedicalRecord, Prescription


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "blood_type", "updated_by", "updated_at")
    search_fields = ("patient__medical_record_number", "patient__last_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "consultation_date", "follow_up_date")
    search_fields = ("patient__medical_record_number", "patient__last_name", "diagnosis")
    list_filter = ("consultation_date",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "medication", "prescription_date", "refills")
    search_fields = ("patient__medical_record_number", "patient__last_name", "medication")
    list_filter = ("prescription_date",)