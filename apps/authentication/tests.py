from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.authentication.models import DoctorProfile, StaffProfile
from apps.medical_records.models import Consultation
from apps.patients.models import Patient
from apps.queue.models import QueueEntry

from .roles import ADMIN, DOCTOR, PATIENT, RECEPTIONIST, get_user_roles


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.password = "temporary-pass-42"
        self.user = self.user_model.objects.create_user(
            username="first-login-user",
            email="user@example.com",
            password=self.password,
        )

    def test_first_login_requires_password_change(self):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": self.user.username, "password": self.password},
        )

        self.assertRedirects(response, reverse("authentication:password_change"))
        self.assertTrue(self.client.session["medimanage_must_change_password"])

    def test_password_change_clears_first_login_requirement(self):
        self.client.login(username=self.user.username, password=self.password)
        self.client.session["medimanage_must_change_password"] = True
        self.client.session.save()

        response = self.client.get(reverse("authentication:password_change"))
        self.assertNotContains(response, "Old password")

        response = self.client.post(
            reverse("authentication:password_change"),
            {
                "new_password1": "permanent-pass-43",
                "new_password2": "permanent-pass-43",
            },
        )

        self.assertRedirects(response, reverse("authentication:password_change_done"))
        self.assertNotIn("medimanage_must_change_password", self.client.session)

    def test_logout_redirects_to_login_and_clears_password_flag(self):
        self.client.login(username=self.user.username, password=self.password)
        self.client.session["medimanage_must_change_password"] = True
        self.client.session.save()

        response = self.client.get(reverse("authentication:logout"))

        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("medimanage_must_change_password", self.client.session)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_role_redirect_uses_superuser_or_group_role(self):
        role_group = Group.objects.create(name="DOCTOR")
        self.user.groups.add(role_group)
        self.user.last_login = self.user.date_joined
        self.user.save(update_fields=["last_login"])
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("authentication:role_redirect"))

        self.assertRedirects(response, reverse("authentication:doctor_dashboard"))

    def test_admin_redirects_to_admin_dashboard(self):
        role_group = Group.objects.create(name=ADMIN)
        self.user.groups.add(role_group)
        self.user.last_login = self.user.date_joined
        self.user.save(update_fields=["last_login"])
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("authentication:role_redirect"))

        self.assertRedirects(response, reverse("authentication:admin_dashboard"))

    def test_setup_page_has_sign_in_and_role_navigation(self):
        response = self.client.get(reverse("setup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")
        self.assertContains(response, "Role-based clinic management")

    def test_authenticated_users_do_not_see_sign_in_link(self):
        self.user.last_login = self.user.date_joined
        self.user.save(update_fields=["last_login"])
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("setup"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign in")
        self.assertContains(response, "Dashboard")

    def test_admin_and_receptionist_headers_show_role_labels(self):
        admin = self.user_model.objects.create_user(username="role-admin", password=self.password)
        admin.groups.add(Group.objects.get_or_create(name=ADMIN)[0])
        self.client.force_login(admin)
        admin_response = self.client.get(reverse("setup"))
        self.assertContains(admin_response, "Admin")
        self.assertContains(admin_response, "Admin dashboard")

        receptionist = self.user_model.objects.create_user(username="role-receptionist", password=self.password)
        receptionist.groups.add(Group.objects.get_or_create(name=RECEPTIONIST)[0])
        self.client.force_login(receptionist)
        receptionist_response = self.client.get(reverse("setup"))
        self.assertContains(receptionist_response, "Receptionist")
        self.assertContains(receptionist_response, "Reception desk")

    def test_receptionist_setup_page_shows_create_patient_quick_action(self):
        response = self.client.get(f"{reverse('setup')}?role=receptionist")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create patient")
        self.assertContains(response, "/patients/register/")

    def test_admin_can_create_staff_account(self):
        admin = self.user_model.objects.create_user(
            username="admin-creator",
            password=self.password,
        )
        admin.groups.add(Group.objects.get_or_create(name=ADMIN)[0])
        self.client.force_login(admin)

        response = self.client.post(
            reverse("authentication:staff_create"),
            {
                "username": "new-staff-user",
                "first_name": "Nina",
                "last_name": "Staff",
                "email": "staff@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "role": RECEPTIONIST,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username: new-staff-user")
        self.assertContains(response, "Password: StrongPass123!")
        created_user = self.user_model.objects.get(username="new-staff-user")
        self.assertTrue(created_user.is_staff)
        self.assertTrue(created_user.groups.filter(name=RECEPTIONIST).exists())
        self.assertEqual(created_user.staff_profile.role, RECEPTIONIST)

    def test_admin_can_create_doctor_account_and_it_appears_in_appointment_scheduling(self):
        admin = self.user_model.objects.create_user(
            username="admin-doctor-creator",
            password=self.password,
        )
        admin.groups.add(Group.objects.get_or_create(name=ADMIN)[0])
        self.client.force_login(admin)

        response = self.client.post(
            reverse("authentication:staff_create"),
            {
                "username": "new-doctor-user",
                "first_name": "Dr.",
                "last_name": "Smith",
                "email": "doctor@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "role": DOCTOR,
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = self.user_model.objects.get(username="new-doctor-user")
        self.assertTrue(created_user.groups.filter(name=DOCTOR).exists())
        self.assertTrue(DoctorProfile.objects.filter(staff_profile__user=created_user).exists())

    def test_receptionist_cannot_create_staff_account(self):
        receptionist = self.user_model.objects.create_user(
            username="receptionist-no-create",
            password=self.password,
        )
        receptionist.groups.add(Group.objects.get_or_create(name=RECEPTIONIST)[0])
        self.client.force_login(receptionist)

        response = self.client.post(
            reverse("authentication:staff_create"),
            {
                "username": "blocked-staff-user",
                "first_name": "Blocked",
                "last_name": "Account",
                "email": "blocked@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "role": RECEPTIONIST,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.user_model.objects.filter(username="blocked-staff-user").exists())


class AdminDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="admin-dashboard-user",
            password="admin-pass-42",
        )
        self.admin_user.groups.add(Group.objects.create(name=ADMIN))

        self.patient = Patient.objects.create(
            first_name="Alice",
            last_name="Doctor",
            email="alice@example.com",
        )

    def test_admin_dashboard_shows_clinic_summary(self):
        self.client.force_login(self.admin_user)

    def test_admin_can_manage_all_staff_accounts(self):
        admin = self.admin_user
        user_model = get_user_model()
        receptionist = user_model.objects.create_user(
            username="staff-manager",
            email="staff@example.com",
            password="admin-pass-42",
        )
        receptionist.groups.add(Group.objects.get_or_create(name=RECEPTIONIST)[0])
        StaffProfile.objects.create(user=receptionist, role=RECEPTIONIST)

        self.client.force_login(admin)

        response = self.client.get(reverse("authentication:staff_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "staff-manager")
        self.assertContains(response, "Deactivate")

        toggle_response = self.client.post(
            reverse("authentication:staff_account_toggle", args=[receptionist.pk]),
            follow=True,
        )
        self.assertEqual(toggle_response.status_code, 200)
        receptionist.refresh_from_db()
        self.assertFalse(receptionist.is_active)

        delete_response = self.client.post(
            reverse("authentication:staff_account_delete", args=[receptionist.pk]),
            follow=True,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(user_model.objects.filter(pk=receptionist.pk).exists())

        response = self.client.get(reverse("authentication:admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("authentication:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clinic overview")
        self.assertContains(response, "Patients")
        self.assertContains(response, "Appointments")
        self.assertContains(response, "Create patient")


class DoctorDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.doctor_user = user_model.objects.create_user(
            username="doctor-dashboard-user",
            password="doctor-pass-42",
        )
        self.doctor_user.groups.add(Group.objects.create(name=DOCTOR))
        self.doctor_staff = StaffProfile.objects.create(
            user=self.doctor_user,
            role=DOCTOR,
            employee_id="DOC-DASH-001",
        )
        self.doctor = DoctorProfile.objects.create(
            staff_profile=self.doctor_staff,
            specialization="Family Medicine",
            license_number="LIC-DASH-001",
        )
        self.patient = Patient.objects.create(
            first_name="Alice",
            last_name="Doctor",
            email="alice@example.com",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(hours=1),
            reason="Follow up",
            created_by=self.doctor_user,
        )
        Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis="Improved symptoms",
            treatment="Continue monitoring",
            clinical_notes="Good progress.",
        )

    def test_doctor_dashboard_shows_all_appointments_and_recent_consultations(self):
        future_patient = Patient.objects.create(
            first_name="Bob",
            last_name="Smith",
            email="bob@example.com",
        )
        Appointment.objects.create(
            patient=future_patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(days=3),
            reason="Follow-up review",
            created_by=self.doctor_user,
        )

        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("authentication:doctor_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All appointments")
        self.assertContains(response, "Alice Doctor")
        self.assertContains(response, "Bob Smith")
        self.assertContains(response, "Recent consultations")
        self.assertContains(response, "Improved symptoms")

    def test_doctor_can_reschedule_his_appointment(self):
        self.client.force_login(self.doctor_user)
        new_time = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("appointments:status_update", args=[self.appointment.pk]),
            {
                "doctor": self.doctor.pk,
                "scheduled_for": new_time.strftime("%Y-%m-%dT%H:%M"),
                "status": Appointment.SCHEDULED,
                "notes": "Rescheduled for review.",
            },
            follow=True,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.appointment.doctor_id, self.doctor.pk)
        self.assertEqual(self.appointment.status, Appointment.SCHEDULED)
        self.assertContains(response, "Appointment status updated")

    def test_doctor_dashboard_shows_active_waiting_patients(self):
        waiting_patient = Patient.objects.create(
            first_name="Cora",
            last_name="Brown",
            email="cora@example.com",
        )
        waiting_appointment = Appointment.objects.create(
            patient=waiting_patient,
            doctor=self.doctor,
            scheduled_for=timezone.now() + timedelta(hours=5),
            reason="Check-up",
            status=Appointment.WAITING,
            created_by=self.doctor_user,
        )
        QueueEntry.objects.create(
            patient=waiting_patient,
            appointment=waiting_appointment,
            status=QueueEntry.WAITING,
            queue_number=3,
            notes="Check-in complete",
            created_by=self.doctor_user,
        )

        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("authentication:doctor_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#3")
        self.assertContains(response, "Cora Brown")
        self.assertContains(response, "Check-up")

    def test_doctor_dashboard_search_results_include_record_links(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("authentication:doctor_dashboard"), {"q": "Alice"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View record")
        self.assertContains(response, reverse("medical_records:patient_record", args=[self.patient.pk]))


class RoleAuthorizationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.password = "role-password-42"

    def create_role_user(self, username, role, **extra_fields):
        user = self.user_model.objects.create_user(
            username=username,
            password=self.password,
            **extra_fields,
        )
        user.groups.add(Group.objects.get_or_create(name=role)[0])
        return user

    def test_role_helpers_use_canonical_groups(self):
        doctor = self.create_role_user("doctor-user", DOCTOR)

        self.assertEqual(get_user_roles(doctor), {DOCTOR})

    def test_patient_cannot_open_receptionist_area(self):
        patient = self.create_role_user("patient-user", PATIENT)
        self.client.force_login(patient)

        response = self.client.get(reverse("authentication:receptionist_access_check"))

        self.assertEqual(response.status_code, 403)

    def test_patient_can_only_open_their_own_record(self):
        patient = self.create_role_user("patient-user", PATIENT)
        another_patient = self.create_role_user("another-patient", PATIENT)
        self.client.force_login(patient)

        own_response = self.client.get(
            reverse(
                "authentication:patient_record_access_check",
                args=[patient.pk],
            )
        )
        other_response = self.client.get(
            reverse(
                "authentication:patient_record_access_check",
                args=[another_patient.pk],
            )
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 403)

    def test_receptionist_cannot_open_administrator_area(self):
        receptionist = self.create_role_user("receptionist-user", RECEPTIONIST)
        self.client.force_login(receptionist)

        response = self.client.get(reverse("authentication:administrator_access_check"))

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_open_administrator_area(self):
        doctor = self.create_role_user("doctor-user", DOCTOR)
        self.client.force_login(doctor)

        response = self.client.get(reverse("authentication:administrator_access_check"))

        self.assertEqual(response.status_code, 403)

    def test_non_administrator_cannot_open_django_admin(self):
        receptionist = self.create_role_user("receptionist-user", RECEPTIONIST)
        receptionist.is_staff = True
        receptionist.save(update_fields=["is_staff"])
        self.client.force_login(receptionist)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_open_django_admin(self):
        admin = self.user_model.objects.create_superuser(
            username="admin-user",
            password=self.password,
        )
        self.client.force_login(admin)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
"""Tests for the authentication application."""