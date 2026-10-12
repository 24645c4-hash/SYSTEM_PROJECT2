"""Tests for the medical records application."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import DoctorProfile, StaffProfile
from apps.authentication.roles import DOCTOR, PATIENT
from apps.patients.models import Patient

from .models import Consultation, MedicalRecord, Prescription


class MedicalRecordsWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.doctor_user = user_model.objects.create_user(
            username="chart-doctor",
            first_name="Dr",
            last_name="Chart",
        )
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.doctor_staff = StaffProfile.objects.create(
            user=self.doctor_user,
            role=DOCTOR,
            employee_id="DOC-CHART-001",
        )
        self.doctor = DoctorProfile.objects.create(
            staff_profile=self.doctor_staff,
            specialization="Family Medicine",
            license_number="LIC-CHART-001",
        )

        self.patient_user = user_model.objects.create_user(
            username="chart-patient",
            first_name="Chart",
            last_name="Patient",
        )
        self.patient_user.groups.add(Group.objects.create(name=PATIENT))
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name="Chart",
            last_name="Patient",
            email="chart@example.com",
        )

    def test_blood_type_uses_standardized_choices(self):
        field = MedicalRecord._meta.get_field("blood_type")

        self.assertIn(("A+", "A+"), field.choices)
        self.assertIn(("O-", "O-"), field.choices)

    def test_doctor_can_create_a_consultation_for_a_patient(self):
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("medical_records:consultation_create", args=[self.patient.pk]),
            {
                "chief_complaint": "Recurring fever",
                "diagnosis": "Seasonal allergy",
                "treatment": "Antihistamine and monitoring",
                "clinical_notes": "Symptoms improved after rest.",
                "follow_up_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        consultation = Consultation.objects.get(patient=self.patient)
        self.assertEqual(consultation.diagnosis, "Seasonal allergy")

    def test_doctor_can_create_a_prescription_for_a_patient(self):
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("medical_records:prescription_create", args=[self.patient.pk]),
            {
                "medication": "Cetirizine",
                "dosage": "10 mg",
                "instructions": "Take once daily for 7 days.",
                "prescription_date": timezone.localdate().isoformat(),
                "duration_days": 7,
                "quantity": "14 tablets",
                "refills": 1,
            },
        )

        self.assertEqual(response.status_code, 302)
        prescription = Prescription.objects.get(patient=self.patient, medication="Cetirizine")
        self.assertEqual(prescription.dosage, "10 mg")

    def test_patient_cannot_edit_clinical_summary_or_medical_record(self):
        self.client.force_login(self.patient_user)

        response = self.client.get(reverse("medical_records:record_update", args=[self.patient.pk]))

        self.assertEqual(response.status_code, 403)

    def test_patient_record_view_shows_a_care_timeline_for_recent_events(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            allergies="Penicillin",
            chronic_conditions="Asthma",
            updated_by=self.doctor_user,
        )
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Cough",
            diagnosis="Seasonal allergy",
            treatment="Cetirizine",
            clinical_notes="Patient reports improvement.",
        )
        Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            consultation=consultation,
            medication="Cetirizine",
            dosage="10 mg",
            instructions="Take once daily.",
        )

        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("medical_records:patient_record", args=[self.patient.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Care timeline")
        self.assertContains(response, "Consultation")
        self.assertContains(response, "Prescription")
        self.assertContains(response, "Seasonal allergy")
        self.assertContains(response, "Cetirizine")

    def test_patient_record_view_lists_medical_summary_and_recent_clinical_notes(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            allergies="Penicillin",
            chronic_conditions="Asthma",
            updated_by=self.doctor_user,
        )
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Cough",
            diagnosis="Seasonal allergy",
            treatment="Cetirizine",
            clinical_notes="Patient reports improvement.",
        )
        Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            consultation=consultation,
            medication="Cetirizine",
            dosage="10 mg",
            instructions="Take once daily.",
        )

        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("medical_records:patient_record", args=[self.patient.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Penicillin")
        self.assertContains(response, "Seasonal allergy")
        self.assertContains(response, "Cetirizine")