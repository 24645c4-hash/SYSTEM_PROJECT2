"""Views for the medical records application."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.authentication.models import DoctorProfile
from apps.authentication.permissions import role_required
from apps.authentication.roles import ADMIN, DOCTOR, PATIENT, RECEPTIONIST, user_has_any_role
from apps.patients.models import Patient

from .forms import ConsultationForm, MedicalRecordForm, PrescriptionForm
from .models import Consultation, MedicalRecord, Prescription


def _can_view_patient_record(user, patient: Patient) -> bool:
    if user_has_any_role(user, (ADMIN, RECEPTIONIST, DOCTOR)):
        return True
    if user_has_any_role(user, (PATIENT,)) and patient.user_id == user.pk:
        return True
    return False


@login_required
def patient_record(request, patient_id):
    """Display a patient's summary, consultations, and active prescriptions."""

    patient = get_object_or_404(Patient.objects.select_related("user"), pk=patient_id)
    if not _can_view_patient_record(request.user, patient):
        raise PermissionDenied

    medical_record, _ = MedicalRecord.objects.get_or_create(patient=patient)
    consultations = Consultation.objects.filter(patient=patient).select_related(
        "doctor__staff_profile__user"
    ).order_by("-consultation_date")[:10]
    prescriptions = Prescription.objects.filter(patient=patient).select_related(
        "doctor__staff_profile__user"
    ).order_by("-prescription_date", "-created_at")[:10]

    care_timeline = []
    for consultation in consultations:
        care_timeline.append(
            {
                "type": "Consultation",
                "date": consultation.consultation_date.date(),
                "title": consultation.diagnosis or consultation.chief_complaint or "Consultation",
                "summary": consultation.clinical_notes or consultation.treatment or "No notes recorded.",
            }
        )
    for prescription in prescriptions:
        care_timeline.append(
            {
                "type": "Prescription",
                "date": prescription.prescription_date,
                "title": prescription.medication,
                "summary": prescription.instructions or "Prescription added.",
            }
        )
    care_timeline = sorted(care_timeline, key=lambda item: item["date"], reverse=True)[:8]

    return render(
        request,
        "medical_records/patient_record.html",
        {
            "patient": patient,
            "medical_record": medical_record,
            "consultations": consultations,
            "prescriptions": prescriptions,
            "care_timeline": care_timeline,
            "can_manage_patients": user_has_any_role(request.user, (ADMIN, RECEPTIONIST)),
            "can_document_patient": user_has_any_role(request.user, (DOCTOR,)),
        },
    )


@role_required(DOCTOR)
def consultation_create(request, patient_id):
    """Create a consultation note for a patient."""

    patient = get_object_or_404(Patient, pk=patient_id)
    doctor_profile = DoctorProfile.objects.filter(staff_profile__user=request.user).first()
    if doctor_profile is None:
        raise PermissionDenied

    if request.method == "POST":
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.doctor = doctor_profile
            consultation.save()
            messages.success(request, "Consultation notes were saved.")
            return redirect("medical_records:patient_record", patient.pk)
    else:
        form = ConsultationForm()

    return render(
        request,
        "medical_records/consultation_form.html",
        {"patient": patient, "form": form},
    )


@role_required(DOCTOR)
def medical_record_update(request, patient_id):
    """Update the structured summary for a patient."""

    patient = get_object_or_404(Patient, pk=patient_id)
    medical_record, _ = MedicalRecord.objects.get_or_create(patient=patient)

    if request.method == "POST":
        form = MedicalRecordForm(request.POST, instance=medical_record)
        if form.is_valid():
            record = form.save(commit=False)
            record.updated_by = request.user
            record.save()
            messages.success(request, "Medical record updated.")
            return redirect("medical_records:patient_record", patient.pk)
    else:
        form = MedicalRecordForm(instance=medical_record)

    return render(
        request,
        "medical_records/record_form.html",
        {"patient": patient, "form": form, "medical_record": medical_record},
    )


@role_required(DOCTOR)
def prescription_create(request, patient_id):
    """Create a prescription for a patient during or after a consultation."""

    patient = get_object_or_404(Patient, pk=patient_id)
    doctor_profile = DoctorProfile.objects.filter(staff_profile__user=request.user).first()
    if doctor_profile is None:
        raise PermissionDenied

    if request.method == "POST":
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.patient = patient
            prescription.doctor = doctor_profile
            prescription.save()
            messages.success(request, "Prescription added.")
            return redirect("medical_records:patient_record", patient.pk)
    else:
        form = PrescriptionForm()

    return render(
        request,
        "medical_records/prescription_form.html",
        {"patient": patient, "form": form},
    )
