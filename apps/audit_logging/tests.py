"""Tests for the audit logging application."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.audit_logging.models import AuditLog
from apps.authentication.roles import ADMIN


class AuditLogListTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(username="audit-admin")
        self.admin.groups.add(Group.objects.create(name=ADMIN))
        self.audit_event = AuditLog.objects.create(
            user=self.admin,
            action="PATIENT_CREATED",
            description="A patient was created.",
        )

    def test_admin_can_view_audit_logs(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("audit_logging:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PATIENT_CREATED")
        self.assertContains(response, str(self.audit_event.pk))
