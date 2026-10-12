"""Tests for the reports application."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.audit_logging.models import AuditLog
from apps.authentication.roles import ADMIN
from apps.patients.models import Patient


class ReportDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(username="report-admin")
        self.admin.groups.add(Group.objects.create(name=ADMIN))
        Patient.objects.create(first_name="Report", last_name="Patient")

    def test_admin_can_view_report_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("reports:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clinic reports")
        self.assertContains(response, "Patients")

    def test_audit_activity_is_visible_on_report_dashboard(self):
        AuditLog.objects.create(
            user=self.admin,
            action="REPORT_VIEWED",
            description="Reports overview opened.",
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("reports:dashboard"))

        self.assertContains(response, "REPORT_VIEWED")
