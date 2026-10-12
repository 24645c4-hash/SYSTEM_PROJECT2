from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import override_settings
from django.test import TestCase
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit_logging.models import AuditLog
from apps.authentication.models import DoctorProfile, StaffProfile
from apps.authentication.roles import ADMIN, DOCTOR, RECEPTIONIST
from apps.medical_records.models import Consultation, MedicalRecord, Prescription
from apps.notifications.models import Notification
from apps.authentication.roles import PATIENT

from .models import Patient


class CoreModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.receptionist_user = user_model.objects.create_user(
            username="receptionist",
            first_name="Rina",
            last_name="Frontdesk",
        )
        self.receptionist_user.groups.add(Group.objects.create(name=RECEPTIONIST))
        self.doctor_user = user_model.objects.create_user(
            username="doctor",
            first_name="David",
            last_name="Doctor",
        )
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.staff = StaffProfile.objects.create(
            user=self.receptionist_user,
            role=RECEPTIONIST,
            employee_id="EMP-001",
        )
        self.doctor_staff = StaffProfile.objects.create(
            user=self.doctor_user,
            role=DOCTOR,
            employee_id="EMP-002",
        )
        self.doctor = DoctorProfile.objects.create(
            staff_profile=self.doctor_staff,
            specialization="Family Medicine",
            license_number="LIC-001",
        )
        self.patient = Patient.objects.create(
            first_name="Pat",
            last_name="Patient",
            date_of_birth=date(1990, 5, 10),
            created_by=self.receptionist_user,
        )

    def test_patient_generates_medical_record_number_and_full_name(self):
        self.assertTrue(self.patient.medical_record_number.startswith("MM-"))
        self.assertEqual(self.patient.get_full_name(), "Pat Patient")
        self.assertEqual(str(self.patient), f"Pat Patient ({self.patient.medical_record_number})")

    def test_staff_and_doctor_profiles_are_linked(self):
        self.assertEqual(self.doctor.staff_profile, self.doctor_staff)
        self.assertEqual(self.doctor_staff.doctor_profile, self.doctor)
        self.assertIn("DOCTOR", str(self.doctor_staff))

    def test_appointment_links_patient_and_doctor(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now(),
            created_by=self.receptionist_user,
        )

        self.assertEqual(appointment.status, Appointment.SCHEDULED)
        self.assertIn(appointment, self.patient.appointments.all())
        self.assertIn(appointment, self.doctor.appointments.all())

    def test_clinical_records_link_to_patient_and_doctor(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            allergies="Penicillin",
            updated_by=self.doctor_user,
        )
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis="Seasonal allergy",
            clinical_notes="Follow up if symptoms persist.",
        )
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            consultation=consultation,
            medication="Cetirizine",
            dosage="10 mg",
            instructions="Take once daily.",
        )

        self.assertEqual(record.patient, self.patient)
        self.assertEqual(consultation.doctor, self.doctor)
        self.assertEqual(prescription.consultation, consultation)

    def test_notifications_and_audit_logs_capture_activity(self):
        notification = Notification.objects.create(
            recipient=self.patient.user or self.receptionist_user,
            patient=self.patient,
            title="Appointment confirmed",
            message="Your appointment is confirmed.",
            notification_type=Notification.APPOINTMENT,
        )
        content_type = ContentType.objects.get_for_model(self.patient)
        audit_log = AuditLog.objects.create(
            user=self.receptionist_user,
            action="PATIENT_CREATED",
            description="Patient profile created.",
            content_type=content_type,
            object_id=str(self.patient.pk),
        )

        self.assertFalse(notification.is_read)
        self.assertEqual(audit_log.content_object, self.patient)
        self.assertIn("PATIENT_CREATED", str(audit_log))


class PatientManagementViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.receptionist = user_model.objects.create_user(username="frontdesk")
        self.receptionist.groups.add(Group.objects.create(name=RECEPTIONIST))
        self.doctor_user = user_model.objects.create_user(username="clinical")
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.patient_user = user_model.objects.create_user(username="patient-account")
        self.patient_user.groups.add(Group.objects.create(name=PATIENT))
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name="Existing",
            last_name="Patient",
            phone="555-0100",
        )

    def test_receptionist_can_register_a_patient_and_audit_action_is_created(self):
        self.client.force_login(self.receptionist)

        response = self.client.post(
            "/patients/register/",
            {
                "first_name": "New",
                "middle_name": "",
                "last_name": "Patient",
                "date_of_birth": "1994-07-12",
                "gender": "FEMALE",
                "email": "new@example.com",
                "phone": "555-0199",
                "address": "12 Clinic Road",
                "emergency_contact_name": "Emergency Contact",
                "emergency_contact_phone": "555-0200",
                "status": "ACTIVE",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Patient.objects.get(email="new@example.com")
        self.assertEqual(created.created_by, self.receptionist)
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_CREATED",
                object_id=str(created.pk),
            ).exists()
        )

    def test_receptionist_can_search_patient_records(self):
        Patient.objects.create(first_name="Maria", last_name="Searchable")
        self.client.force_login(self.receptionist)

        response = self.client.get("/patients/", {"q": "Maria"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Searchable")
        self.assertNotContains(response, "Existing Patient")

    def test_receptionist_can_edit_deactivate_and_archive_patient(self):
        self.client.force_login(self.receptionist)
        update_response = self.client.post(
            f"/patients/{self.patient.pk}/edit/",
            {
                "first_name": "Updated",
                "middle_name": "",
                "last_name": "Patient",
                "date_of_birth": "",
                "gender": "",
                "email": "",
                "phone": "555-0111",
                "address": "",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
                "status": "ACTIVE",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, "Updated")

        deactivate_response = self.client.post(f"/patients/{self.patient.pk}/deactivate/")
        self.assertEqual(deactivate_response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.INACTIVE)

        archive_response = self.client.post(f"/patients/{self.patient.pk}/archive/")
        self.assertEqual(archive_response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.ARCHIVED)
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_ARCHIVED",
                object_id=str(self.patient.pk),
            ).exists()
        )

    def test_doctor_can_view_but_cannot_manage_patient_profiles(self):
        self.client.force_login(self.doctor_user)

        detail_response = self.client.get(f"/patients/{self.patient.pk}/")
        create_response = self.client.get("/patients/register/")
        update_response = self.client.post(f"/patients/{self.patient.pk}/edit/", {})

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)

    def test_patient_can_view_only_their_own_profile(self):
        other_patient = Patient.objects.create(first_name="Other", last_name="Patient")
        self.client.force_login(self.patient_user)

        own_response = self.client.get(f"/patients/{self.patient.pk}/")
        other_response = self.client.get(f"/patients/{other_patient.pk}/")
        list_response = self.client.get("/patients/")

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 403)
        self.assertEqual(list_response.status_code, 403)

    def test_patient_dashboard_is_private_and_audited(self):
        other_user = get_user_model().objects.create_user(username="other-patient")
        other_user.groups.add(Group.objects.get_or_create(name=PATIENT)[0])
        other_patient = Patient.objects.create(
            user=other_user,
            first_name="Other",
            last_name="Patient",
        )
        Notification.objects.create(
            recipient=self.patient_user,
            patient=self.patient,
            title="Your notification",
            message="Only you should see this.",
        )
        Notification.objects.create(
            recipient=other_user,
            patient=other_patient,
            title="Other notification",
            message="This belongs to another patient.",
        )
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=DoctorProfile.objects.create(
                staff_profile=StaffProfile.objects.create(
                    user=self.doctor_user,
                    role=DOCTOR,
                    employee_id="EMP-PORTAL",
                ),
                specialization="Family Medicine",
            ),
            scheduled_for=timezone.now(),
            reason="Annual checkup",
        )
        Appointment.objects.create(
            patient=other_patient,
            doctor=appointment.doctor,
            scheduled_for=timezone.now(),
            reason="Other patient's appointment",
        )

        self.client.force_login(self.patient_user)
        response = self.client.get("/patients/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Existing Patient")
        self.assertContains(response, "Your notification")
        self.assertContains(response, "Annual checkup")
        self.assertNotContains(response, "Other notification")
        self.assertNotContains(response, "Other patient's appointment")
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_PORTAL_VIEWED",
                user=self.patient_user,
                object_id=str(self.patient.pk),
            ).exists()
        )

    def test_patient_dashboard_rejects_staff_and_unlinked_patient_users(self):
        self.client.force_login(self.receptionist)
        staff_response = self.client.get("/patients/dashboard/")
        self.assertEqual(staff_response.status_code, 403)

        unlinked_patient = get_user_model().objects.create_user(username="unlinked")
        unlinked_patient.groups.add(Group.objects.get_or_create(name=PATIENT)[0])
        self.client.force_login(unlinked_patient)
        unlinked_response = self.client.get("/patients/dashboard/")
        self.assertEqual(unlinked_response.status_code, 403)

    def test_patient_role_redirects_to_their_dashboard(self):
        self.client.force_login(self.patient_user)

        response = self.client.get("/auth/redirect/")

        self.assertRedirects(response, "/patients/dashboard/")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_receptionist_can_create_patient_account_and_email_temporary_password(self):
        activation_patient = Patient.objects.create(
            first_name="New",
            last_name="Patient",
            email="patient@example.com",
        )
        self.client.force_login(self.receptionist)

        response = self.client.post(
            f"/patients/{activation_patient.pk}/activate-account/",
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        activation_patient.refresh_from_db()
        self.assertIsNotNone(activation_patient.user)
        self.assertTrue(activation_patient.user.groups.filter(name=PATIENT).exists())
        self.assertEqual(activation_patient.user.email, activation_patient.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(activation_patient.user.username, mail.outbox[0].body)
        self.assertIn("Temporary password:", mail.outbox[0].body)
        self.assertContains(response, "Username:")
        self.assertContains(response, activation_patient.user.username)
        self.assertContains(response, "Temporary password:")
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_ACCOUNT_CREATED",
                user=self.receptionist,
                object_id=str(activation_patient.pk),
            ).exists()
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_receptionist_can_resend_activation_with_a_new_temporary_password(self):
        activation_patient = Patient.objects.create(
            first_name="Resend",
            last_name="Patient",
            email="resend@example.com",
        )
        self.client.force_login(self.receptionist)
        self.client.post(f"/patients/{activation_patient.pk}/activate-account/")
        activation_patient.refresh_from_db()
        first_email = mail.outbox[0].body
        first_temporary_password = first_email.split(
            "Temporary password: ", 1
        )[1].split("\n", 1)[0]
        first_user = activation_patient.user

        response = self.client.post(
            f"/patients/{activation_patient.pk}/resend-activation/",
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        second_email = mail.outbox[1].body
        second_temporary_password = second_email.split(
            "Temporary password: ", 1
        )[1].split("\n", 1)[0]
        self.assertNotEqual(first_temporary_password, second_temporary_password)
        first_user.refresh_from_db()
        self.assertFalse(first_user.check_password(first_temporary_password))
        self.assertTrue(first_user.check_password(second_temporary_password))
        self.assertIsNone(first_user.last_login)
        self.assertContains(response, "Username:")
        self.assertContains(response, activation_patient.user.username)
        self.assertContains(response, "Temporary password:")
        self.assertContains(response, second_temporary_password)
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_ACCOUNT_ACTIVATION_RESEND_ATTEMPTED",
                user=self.receptionist,
                object_id=str(activation_patient.pk),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_ACCOUNT_ACTIVATION_RESENT",
                user=self.receptionist,
                object_id=str(activation_patient.pk),
            ).exists()
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_resend_temporary_password_still_forces_first_login_password_change(self):
        activation_patient = Patient.objects.create(
            first_name="Reset",
            last_name="Patient",
            email="reset@example.com",
        )
        self.client.force_login(self.receptionist)
        self.client.post(f"/patients/{activation_patient.pk}/activate-account/")
        self.client.post(f"/patients/{activation_patient.pk}/resend-activation/")
        activation_patient.refresh_from_db()
        temporary_password = mail.outbox[-1].body.split(
            "Temporary password: ", 1
        )[1].split("\n", 1)[0]

        self.client.logout()
        response = self.client.post(
            "/auth/login/",
            {
                "username": activation_patient.user.username,
                "password": temporary_password,
            },
        )

        self.assertRedirects(response, "/auth/password-change/")
        self.assertTrue(self.client.session["medimanage_must_change_password"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_doctor_cannot_resend_patient_activation(self):
        activation_patient = Patient.objects.create(
            first_name="Protected",
            last_name="Patient",
            email="protected@example.com",
        )
        self.client.force_login(self.receptionist)
        self.client.post(f"/patients/{activation_patient.pk}/activate-account/")
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            f"/patients/{activation_patient.pk}/resend-activation/"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_administrator_can_resend_patient_activation(self):
        activation_patient = Patient.objects.create(
            first_name="Admin",
            last_name="Resend",
            email="admin-resend@example.com",
        )
        self.client.force_login(self.receptionist)
        self.client.post(f"/patients/{activation_patient.pk}/activate-account/")
        admin = get_user_model().objects.create_superuser(
            username="resend-admin",
            password="admin-password-42",
        )
        self.client.force_login(admin)

        response = self.client.post(
            f"/patients/{activation_patient.pk}/resend-activation/"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)

    def test_only_administrators_and_receptionists_can_create_patient_accounts(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(f"/patients/{self.patient.pk}/activate-account/")
        self.assertEqual(response.status_code, 403)

        admin = get_user_model().objects.create_superuser(
            username="account-admin",
            password="admin-password-42",
        )
        unlinked_patient = Patient.objects.create(
            first_name="Unlinked",
            last_name="Patient",
            email="unlinked@example.com",
        )
        self.client.force_login(admin)
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ):
            response = self.client.post(
                f"/patients/{unlinked_patient.pk}/activate-account/"
            )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(
            Patient.objects.get(pk=unlinked_patient.pk).user_id
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_activation_requires_active_profile_and_email(self):
        activation_patient = Patient.objects.create(
            first_name="Inactive",
            last_name="Patient",
            status=Patient.INACTIVE,
        )
        self.client.force_login(self.receptionist)

        response = self.client.post(
            f"/patients/{activation_patient.pk}/activate-account/"
        )

        self.assertEqual(response.status_code, 200)
        activation_patient.refresh_from_db()
        self.assertIsNone(activation_patient.user_id)
        self.assertFalse(
            AuditLog.objects.filter(action="PATIENT_ACCOUNT_CREATED").exists()
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_first_patient_login_is_audited_and_forces_password_change(self):
        activation_patient = Patient.objects.create(
            first_name="First",
            last_name="Login",
            email="patient@example.com",
        )
        self.client.force_login(self.receptionist)
        self.client.post(
            f"/patients/{activation_patient.pk}/activate-account/"
        )
        activation_patient.refresh_from_db()
        activation_email = mail.outbox[0].body
        temporary_password = activation_email.split("Temporary password: ", 1)[1].split(
            "\n", 1
        )[0]

        self.client.logout()
        response = self.client.post(
            "/auth/login/",
            {
                "username": activation_patient.user.username,
                "password": temporary_password,
            },
        )

        self.assertRedirects(response, "/auth/password-change/")
        self.assertTrue(self.client.session["medimanage_must_change_password"])
        self.assertTrue(
            AuditLog.objects.filter(
                action="PATIENT_ACCOUNT_ACTIVATED",
                user=activation_patient.user,
                object_id=str(activation_patient.pk),
            ).exists()
        )

        blocked_response = self.client.get(f"/patients/{activation_patient.pk}/")
        self.assertRedirects(blocked_response, "/auth/password-change/")

        permanent_password = "permanent-patient-pass-42"
        change_response = self.client.post(
            "/auth/password-change/",
            {
                "old_password": temporary_password,
                "new_password1": permanent_password,
                "new_password2": permanent_password,
            },
        )
        self.assertRedirects(change_response, "/auth/password-change/done/")
        self.assertTrue(
            self.client.login(
                username=activation_patient.user.username,
                password=permanent_password,
            )
        )