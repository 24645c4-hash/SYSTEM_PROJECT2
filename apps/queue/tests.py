from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.authentication.models import DoctorProfile, StaffProfile
from apps.authentication.roles import DOCTOR, PATIENT, RECEPTIONIST
from apps.patients.models import Patient

from .models import QueueEntry


class QueueManagementTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.receptionist = user_model.objects.create_user(username="queue-receptionist")
        self.receptionist.groups.add(Group.objects.create(name=RECEPTIONIST))

        self.doctor_user = user_model.objects.create_user(username="queue-doctor")
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.doctor_staff = StaffProfile.objects.create(
            user=self.doctor_user,
            role=DOCTOR,
            employee_id="QUEUE-001",
        )
        self.doctor = DoctorProfile.objects.create(
            staff_profile=self.doctor_staff,
            specialization="Family Medicine",
            license_number="LIC-QUEUE-001",
        )

        self.patient_user = user_model.objects.create_user(username="queue-patient")
        self.patient_user.groups.add(Group.objects.create(name=PATIENT))
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name="Queue",
            last_name="Patient",
            email="queue@example.com",
        )

    def test_receptionist_can_add_patient_to_queue(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=1),
            reason="Check-in",
            created_by=self.receptionist,
        )
        self.client.force_login(self.receptionist)

        response = self.client.post(
            "/queue/add/",
            {"patient": self.patient.pk, "appointment": appointment.pk, "status": QueueEntry.WAITING},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(QueueEntry.objects.filter(patient=self.patient, appointment=appointment).exists())

    def test_doctor_can_update_queue_status(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=1),
            reason="Consultation",
            created_by=self.receptionist,
        )
        queue_entry = QueueEntry.objects.create(
            patient=self.patient,
            appointment=appointment,
            status=QueueEntry.WAITING,
            queue_number=1,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            f"/queue/{queue_entry.pk}/update-status/",
            {"status": QueueEntry.IN_CONSULTATION},
        )

        self.assertEqual(response.status_code, 302)
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, QueueEntry.IN_CONSULTATION)
