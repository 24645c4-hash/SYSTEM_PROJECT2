"""Authentication views and role-aware login routing."""

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeDoneView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit_logging.models import AuditLog
from apps.medical_records.models import Consultation
from apps.patients.models import Patient
from apps.queue.models import QueueEntry

from .forms import MediManagePasswordChangeForm, StaffAccountCreationForm
from .models import DoctorProfile, StaffProfile
from .permissions import patient_owner_required, role_required
from .roles import (
    ADMIN,
    DOCTOR,
    PATIENT,
    RECEPTIONIST,
    ROLE_QUERY_VALUES,
    get_user_roles,
    user_has_any_role,
)

User = get_user_model()


class MediManageLoginView(LoginView):
    """Log users in and require a password change on their first login."""

    template_name = "authentication/login.html"
    redirect_authenticated_user = True
    redirect_field_name = REDIRECT_FIELD_NAME

    def form_valid(self, form):
        first_login = form.get_user().last_login is None
        response = super().form_valid(form)
        if first_login:
            patient = Patient.objects.filter(user=form.get_user()).first()
            if patient:
                AuditLog.objects.create(
                    user=form.get_user(),
                    action="PATIENT_ACCOUNT_ACTIVATED",
                    description=(
                        f"Patient account activated: {patient.get_full_name()}"
                    ),
                    content_object=patient,
                    ip_address=self.request.META.get("REMOTE_ADDR"),
                )
            self.request.session["medimanage_must_change_password"] = True
            return redirect("authentication:password_change")
        return response


class MediManagePasswordChangeView(PasswordChangeView):
    """Allow a signed-in user to change a temporary or existing password."""

    form_class = MediManagePasswordChangeForm
    template_name = "authentication/password_change_form.html"
    success_url = reverse_lazy("authentication:password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.pop("medimanage_must_change_password", None)
        return response


class MediManagePasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "authentication/password_change_done.html"


def medi_manage_logout(request):
    """Clear the session and redirect back to the login page."""
    if hasattr(request, "session"):
        request.session.pop("medimanage_must_change_password", None)
    logout(request)
    return redirect("authentication:login")


@login_required
def role_redirect(request):
    """Route an authenticated user according to their current Django group.

    Patients have a private portal; other roles continue to use the setup page
    until their role-specific dashboards are introduced.
    """

    if request.user.is_superuser:
        role = "ADMIN"
    else:
        role = next(iter(get_user_roles(request.user)), None)

    if request.user.is_superuser or role == ADMIN:
        return redirect("authentication:admin_dashboard")
    if role == PATIENT:
        return redirect("patients:dashboard")
    if role == DOCTOR:
        return redirect("authentication:doctor_dashboard")

    role_value = ROLE_QUERY_VALUES.get(role, "user")
    return redirect(f"{reverse_lazy('setup')}?role={role_value}")


def setup_view(request):
    """Render the home/setup page with receptionist appointment requests."""

    pending_requests = []
    if request.user.is_authenticated and user_has_any_role(request.user, (ADMIN, RECEPTIONIST)):
        pending_requests = Appointment.objects.filter(status=Appointment.REQUESTED).select_related(
            "patient"
        ).order_by("-created_at")[:10]

    return render(request, "setup.html", {"pending_requests": pending_requests})


@role_required(ADMIN)
def admin_dashboard(request):
    """Show a quick clinic operations overview for administrators."""

    total_patients = Patient.objects.count()
    active_patients = Patient.objects.filter(status=Patient.ACTIVE).count()
    appointments_today = Appointment.objects.filter(
        scheduled_for__date=timezone.localdate(),
    ).count()
    waiting_patients = QueueEntry.objects.filter(status=QueueEntry.WAITING).count()
    active_doctors = StaffProfile.objects.filter(role=DOCTOR).count()
    recent_activity = AuditLog.objects.select_related("user").all()[:10]

    return render(
        request,
        "authentication/admin_dashboard.html",
        {
            "total_patients": total_patients,
            "active_patients": active_patients,
            "appointments_today": appointments_today,
            "waiting_patients": waiting_patients,
            "active_doctors": active_doctors,
            "recent_activity": recent_activity,
        },
    )


@role_required(ADMIN)
def staff_create(request):
    """Allow administrators to create a staff account with a role profile."""

    if request.method == "POST":
        form = StaffAccountCreationForm(request.POST)
        if form.is_valid():
            user, _ = form.save()
            messages.success(
                request,
                f"Staff account for {user.get_full_name() or user.username} was created. "
                f"Username: {user.username}. Password: {form.cleaned_data['password1']}",
            )
            return redirect("authentication:admin_dashboard")
    else:
        form = StaffAccountCreationForm()

    return render(request, "authentication/staff_create.html", {"form": form})


@role_required(ADMIN)
def staff_accounts(request):
    """Display all staff accounts for direct admin management."""

    staff_users = (
        User.objects.filter(staff_profile__isnull=False)
        .select_related("staff_profile")
        .order_by("username")
    )

    return render(request, "authentication/staff_accounts.html", {"staff_users": staff_users})


@role_required(ADMIN)
def staff_account_toggle(request, user_id):
    """Deactivate or reactivate a staff account."""

    staff_user = get_object_or_404(User, pk=user_id, staff_profile__isnull=False)
    staff_user.is_active = not staff_user.is_active
    staff_user.save(update_fields=["is_active"])

    if hasattr(staff_user, "staff_profile"):
        staff_user.staff_profile.is_active = staff_user.is_active
        staff_user.staff_profile.save(update_fields=["is_active"])

    action = "activated" if staff_user.is_active else "deactivated"
    messages.success(request, f"Staff account {staff_user.username} was {action}.")
    return redirect("authentication:staff_accounts")


@role_required(ADMIN)
def staff_account_delete(request, user_id):
    """Delete a staff account permanently."""

    staff_user = get_object_or_404(User, pk=user_id, staff_profile__isnull=False)
    username = staff_user.username
    staff_user.delete()
    messages.success(request, f"Staff account {username} was deleted.")
    return redirect("authentication:staff_accounts")


@role_required(DOCTOR)
def doctor_dashboard(request):
    """Serve the doctor dashboard with upcoming appointments and recent clinical context."""

    doctor_profile = DoctorProfile.objects.filter(
        staff_profile__user=request.user
    ).select_related("staff_profile__user").first()

    search_query = request.GET.get("q", "").strip()
    patient_search = []
    if search_query:
        patient_search = Patient.objects.filter(
            Q(first_name__icontains=search_query)
            | Q(middle_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(medical_record_number__icontains=search_query)
            | Q(phone__icontains=search_query)
        )[:10]

    if doctor_profile is None:
        appointments = []
        waiting_patients = []
        consultations = []
    else:
        appointments = Appointment.objects.filter(
            doctor=doctor_profile,
        ).select_related("patient").order_by("-scheduled_for", "-created_at")
        waiting_patients = QueueEntry.objects.filter(
            appointment__doctor=doctor_profile,
            status__in=(QueueEntry.WAITING, QueueEntry.IN_CONSULTATION),
        ).select_related("patient", "appointment")[:10]

        if not waiting_patients.exists():
            waiting_patients = Appointment.objects.filter(
                doctor=doctor_profile,
                status__in=(Appointment.WAITING, Appointment.IN_CONSULTATION),
            ).select_related("patient").order_by("scheduled_for")[:10]
        consultations = Consultation.objects.filter(
            doctor=doctor_profile,
        ).select_related("patient").order_by("-consultation_date")[:10]

    return render(
        request,
        "authentication/doctor_dashboard.html",
        {
            "doctor": doctor_profile,
            "appointments": appointments,
            "waiting_patients": waiting_patients,
            "consultations": consultations,
            "patient_search": patient_search,
            "search_query": search_query,
        },
    )


@role_required(RECEPTIONIST)
def receptionist_access_check(request):
    """Temporary protected endpoint used until the receptionist module exists."""

    return HttpResponse("Receptionist access granted.")


@role_required(DOCTOR)
def doctor_access_check(request):
    """Temporary protected endpoint used until the doctor module exists."""

    return HttpResponse("Doctor access granted.")


@role_required(PATIENT)
def patient_access_check(request):
    """Temporary protected endpoint used until the patient portal exists."""

    return HttpResponse("Patient access granted.")


@patient_owner_required
def patient_record_access_check(request, patient_user_id):
    """Temporary ownership-protected endpoint for the patient-record rule."""

    return HttpResponse(f"Patient record access granted for user {patient_user_id}.")


@role_required(ADMIN)
def administrator_access_check(request):
    """Temporary protected endpoint used until the administrator module exists."""

    return HttpResponse("Administrator access granted.")