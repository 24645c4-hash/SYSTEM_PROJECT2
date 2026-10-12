"""Tests for the appointments application."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import DoctorProfile, StaffProfile
from apps.authentication.roles import DOCTOR, PATIENT, RECEPTIONIST
from apps.patients.models import Patient

from .models import Appointment


class AppointmentManagementTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.receptionist = user_model.objects.create_user(
            username="frontdesk",
            first_name="Front",
            last_name="Desk",
        )
        self.receptionist.groups.add(Group.objects.create(name=RECEPTIONIST))

        self.doctor_user = user_model.objects.create_user(
            username="doctor-user",
            first_name="Dr",
            last_name="Jones",
        )
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.doctor_staff = StaffProfile.objects.create(
            user=self.doctor_user,
            role=DOCTOR,
            employee_id="DOC-001",
        )
        self.doctor = DoctorProfile.objects.create(
            staff_profile=self.doctor_staff,
            specialization="Family Medicine",
            license_number="LIC-001",
        )

        self.patient_user = user_model.objects.create_user(
            username="patient-user",
            first_name="Patient",
            last_name="User",
        )
        self.patient_user.groups.add(Group.objects.create(name=PATIENT))
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name="Patient",
            last_name="User",
            email="patient@example.com",
        )
        self.other_patient = Patient.objects.create(
            first_name="Other",
            last_name="Patient",
            email="other@example.com",
        )

    def test_receptionist_can_create_and_list_appointments(self):
        self.client.force_login(self.receptionist)

        response = self.client.post(
            "/appointments/create/",
            {
                "patient": self.patient.pk,
                "doctor": self.doctor.pk,
                "scheduled_for": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "status": Appointment.SCHEDULED,
                "reason": "Annual checkup",
                "notes": "Bring previous records.",
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(patient=self.patient, doctor=self.doctor)
        self.assertEqual(appointment.reason, "Annual checkup")

        list_response = self.client.get("/appointments/")
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Annual checkup")

    def test_patient_can_only_view_their_own_appointments(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=2),
            reason="Follow-up check",
            created_by=self.receptionist,
        )
        Appointment.objects.create(
            patient=self.other_patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=3),
            reason="Other appointment",
            created_by=self.receptionist,
        )

        self.client.force_login(self.patient_user)
        response = self.client.get("/appointments/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Follow-up check")
        self.assertNotContains(response, "Other appointment")

    def test_patient_can_request_appointment_with_reason(self):
        self.client.force_login(self.patient_user)

        response = self.client.post(
            "/appointments/request/",
            {
                "reason": "I need a follow-up consultation",
                "notes": "Please review my recent symptoms.",
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(patient=self.patient, reason="I need a follow-up consultation")
        self.assertEqual(appointment.status, Appointment.REQUESTED)
        self.assertIsNone(appointment.doctor_id)
        self.assertIsNone(appointment.scheduled_for)

    def test_patient_without_profile_is_auto_created_before_requesting_appointment(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="new-patient-no-profile",
            first_name="New",
            last_name="Patient",
        )
        user.groups.add(Group.objects.get_or_create(name=PATIENT)[0])
        self.client.force_login(user)

        response = self.client.get("/appointments/request/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Patient.objects.filter(user=user).exists())

        response = self.client.post(
            "/appointments/request/",
            {
                "reason": "I need an urgent follow-up",
                "notes": "Please contact me as soon as possible.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Appointment.objects.filter(
                patient__user=user,
                reason="I need an urgent follow-up",
            ).exists()
        )

    def test_receptionist_can_acknowledge_request_and_schedule_doctor(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=None,
            scheduled_for=None,
            status=Appointment.REQUESTED,
            reason="Follow-up appointment requested",
            created_by=self.patient_user,
        )
        self.client.force_login(self.receptionist)

        response = self.client.post(
            f"/appointments/{appointment.pk}/status/",
            {
                "doctor": self.doctor.pk,
                "scheduled_for": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                "status": Appointment.SCHEDULED,
                "notes": "Acknowledged and scheduled by reception.",
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.status, Appointment.SCHEDULED)

    def test_receptionist_sees_pending_requests_in_a_clear_queue(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=None,
            scheduled_for=None,
            status=Appointment.REQUESTED,
            reason="Needs a new appointment request",
            created_by=self.patient_user,
        )
        self.client.force_login(self.receptionist)

        response = self.client.get("/appointments/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending requests")
        self.assertContains(response, "Needs a new appointment request")

    def test_receptionist_setup_page_lists_pending_requests(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=None,
            scheduled_for=None,
            status=Appointment.REQUESTED,
            reason="Please review this request",
            created_by=self.patient_user,
        )
        self.client.force_login(self.receptionist)

        response = self.client.get("/?role=receptionist")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Show requests")
        self.assertContains(response, "Please review this request")
        self.assertContains(response, "Schedule now")

    def test_doctor_can_update_appointment_status(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=4),
            reason="Consultation",
            created_by=self.receptionist,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            f"/appointments/{appointment.pk}/status/",
            {"status": Appointment.CONFIRMED},
        )

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.CONFIRMED)
