"""URL configuration for the medical records application."""

from django.urls import path

from .views import consultation_create, medical_record_update, patient_record, prescription_create

app_name = "medical_records"

urlpatterns = [
    path("<int:patient_id>/", patient_record, name="patient_record"),
    path("<int:patient_id>/consultation/", consultation_create, name="consultation_create"),
    path("<int:patient_id>/record/", medical_record_update, name="record_update"),
    path("<int:patient_id>/prescription/", prescription_create, name="prescription_create"),
]