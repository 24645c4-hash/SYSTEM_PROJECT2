"""Tests for the notifications application."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.authentication.roles import PATIENT
from apps.patients.models import Patient

from .models import Notification


class NotificationWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.patient_user = user_model.objects.create_user(
            username="patient-notify",
            first_name="Pat",
            last_name="User",
        )
        self.patient_user.groups.add(Group.objects.create(name=PATIENT))
        self.other_user = user_model.objects.create_user(username="other-user")
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name="Pat",
            last_name="User",
            email="pat@example.com",
        )
        self.other_patient = Patient.objects.create(
            user=self.other_user,
            first_name="Other",
            last_name="User",
        )

    def test_patient_can_view_only_their_own_notifications(self):
        own = Notification.objects.create(
            recipient=self.patient_user,
            patient=self.patient,
            title="Appointment reminder",
            message="Your appointment is tomorrow.",
            notification_type=Notification.APPOINTMENT,
        )
        Notification.objects.create(
            recipient=self.other_user,
            patient=self.other_patient,
            title="Private message",
            message="This note belongs to another user.",
            notification_type=Notification.SYSTEM,
        )

        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("notifications:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Appointment reminder")
        self.assertNotContains(response, "Private message")
        self.assertContains(response, str(own.id))

    def test_patient_can_mark_a_notification_as_read(self):
        notification = Notification.objects.create(
            recipient=self.patient_user,
            patient=self.patient,
            title="Follow-up ready",
            message="Your follow-up note is available.",
            notification_type=Notification.FOLLOW_UP,
        )

        self.client.force_login(self.patient_user)
        response = self.client.post(reverse("notifications:mark_read", args=[notification.pk]))

        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
