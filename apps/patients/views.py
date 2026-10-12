"""Patient registration and profile management views."""

import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.appointments.models import Appointment
from apps.audit_logging.models import AuditLog
from apps.authentication.permissions import role_required
from apps.authentication.roles import (
    ADMIN,
    DOCTOR,
    PATIENT,
    RECEPTIONIST,
    user_has_any_role,
)
from apps.notifications.models import Notification

from .forms import PatientAccountActivationForm, PatientForm
from .models import Patient


PATIENT_VIEW_ROLES = (ADMIN, RECEPTIONIST, DOCTOR)
PATIENT_MANAGE_ROLES = (ADMIN, RECEPTIONIST)
User = get_user_model()


def _record_patient_audit(request: HttpRequest, action: str, patient: Patient) -> None:
    AuditLog.objects.create(
        user=request.user,
        action=action,
        description=f"{action.replace('_', ' ').title()}: {patient.get_full_name()}",
        content_object=patient,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


def _patient_username(patient: Patient) -> str:
    """Use the stable medical record number as the patient's login username."""

    return f"patient-{patient.medical_record_number.lower()}"


def _get_or_create_patient_profile(user) -> Patient | None:
    """Ensure a patient-role account has a linked patient profile."""

    if not user_has_any_role(user, (PATIENT,)):
        return None

    patient = Patient.objects.filter(user=user).first()
    if patient is not None:
        return patient

    return Patient.objects.create(
        user=user,
        first_name=user.first_name or user.username,
        last_name=user.last_name or "Patient",
        email=user.email or "",
    )


def _temporary_password() -> str:
    """Generate a credential that is never shown to clinic staff."""

    return secrets.token_urlsafe(18)


def _send_patient_activation_email(
    patient: Patient,
    username: str,
    temporary_password: str,
) -> None:
    """Send activation credentials directly to the patient, never to clinic staff."""

    send_mail(
        subject="Your MediManage patient account",
        message=(
            f"Hello {patient.get_full_name()},\n\n"
            "Your MediManage patient account is ready to use.\n\n"
            f"Username: {username}\n"
            f"Temporary password: {temporary_password}\n\n"
            "Sign in with these temporary credentials. You will be required "
            "to choose a private permanent password on your first login.\n\n"
            "Please do not share your password with clinic staff."
        ),
        from_email=None,
        recipient_list=[patient.email],
        fail_silently=False,
    )


def _can_view_patient(user, patient: Patient) -> bool:
    if user_has_any_role(user, PATIENT_VIEW_ROLES):
        return True
    return user_has_any_role(user, (PATIENT,)) and patient.user_id == user.pk


@role_required(*PATIENT_VIEW_ROLES)
def patient_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    patients = Patient.objects.select_related("user", "created_by")
    if query:
        patients = patients.filter(
            Q(medical_record_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    if status in {choice[0] for choice in Patient.STATUS_CHOICES}:
        patients = patients.filter(status=status)

    return render(
        request,
        "patients/patient_list.html",
        {
            "patients": patients,
            "query": query,
            "selected_status": status,
            "status_choices": Patient.STATUS_CHOICES,
            "can_manage_patients": user_has_any_role(request.user, PATIENT_MANAGE_ROLES),
        },
    )


@role_required(PATIENT)
def patient_dashboard(request: HttpRequest) -> HttpResponse:
    """Show an authenticated patient only the records linked to their account."""

    patient = Patient.objects.filter(user=request.user).first()
    if patient is None:
        patient = _get_or_create_patient_profile(request.user)
        if patient is not None:
            messages.info(
                request,
                "Your patient profile was created automatically. You can now request appointments and view your record.",
            )
    if patient is None:
        raise PermissionDenied

    notifications = Notification.objects.filter(
        recipient=request.user,
        patient=patient,
    )[:10]
    appointments = (
        Appointment.objects.filter(patient=patient)
        .select_related("doctor__staff_profile__user")
    )
    _record_patient_audit(request, "PATIENT_PORTAL_VIEWED", patient)

    return render(
        request,
        "patients/patient_dashboard.html",
        {
            "patient": patient,
            "notifications": notifications,
            "appointments": appointments,
        },
    )


@role_required(*PATIENT_MANAGE_ROLES)
def patient_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            _record_patient_audit(request, "PATIENT_CREATED", patient)
            messages.success(request, f"Patient {patient.get_full_name()} was registered.")
            return redirect("patients:detail", pk=patient.pk)
    else:
        form = PatientForm()

    return render(request, "patients/patient_form.html", {"form": form, "is_edit": False})


@login_required
def patient_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = get_object_or_404(Patient.objects.select_related("user", "created_by"), pk=pk)
    if not _can_view_patient(request.user, patient):
        raise PermissionDenied

    return render(
        request,
        "patients/patient_detail.html",
        {
            "patient": patient,
            "can_manage_patients": user_has_any_role(request.user, PATIENT_MANAGE_ROLES),
        },
    )


@role_required(*PATIENT_MANAGE_ROLES)
def patient_activate_account(request: HttpRequest, pk: int) -> HttpResponse:
    """Create a restricted patient account and email its temporary credential."""

    patient = get_object_or_404(Patient, pk=pk)
    form = PatientAccountActivationForm(
        request.POST if request.method == "POST" else None,
        patient=patient,
    )

    if request.method == "POST" and form.is_valid():
        username = _patient_username(patient)
        if User.objects.filter(username=username).exists():
            form.add_error(
                None,
                "A login with this medical record number already exists. Contact an administrator.",
            )
        else:
            temporary_password = _temporary_password()
            with transaction.atomic():
                patient_user = User.objects.create_user(
                    username=username,
                    first_name=patient.first_name,
                    last_name=patient.last_name,
                    email=patient.email,
                    password=temporary_password,
                )
                patient_user.groups.add(Group.objects.get_or_create(name=PATIENT)[0])
                patient.user = patient_user
                patient.save(update_fields=("user", "updated_at"))
                _record_patient_audit(request, "PATIENT_ACCOUNT_CREATED", patient)
                _send_patient_activation_email(patient, username, temporary_password)

            messages.success(
                request,
                f"Patient account created. Username: {username}. Temporary password: {temporary_password}. "
                f"An activation email was also sent to {patient.email}.",
            )
            return redirect("patients:detail", pk=patient.pk)

    return render(
        request,
        "patients/patient_activate_account.html",
        {"patient": patient, "form": form},
    )


@role_required(*PATIENT_MANAGE_ROLES)
@require_POST
def patient_resend_activation(request: HttpRequest, pk: int) -> HttpResponse:
    """Replace a linked patient's temporary credential and email it to them."""

    patient = get_object_or_404(Patient.objects.select_related("user"), pk=pk)
    _record_patient_audit(
        request,
        "PATIENT_ACCOUNT_ACTIVATION_RESEND_ATTEMPTED",
        patient,
    )

    if patient.user_id is None:
        messages.error(request, "This patient does not have a linked account.")
        return redirect("patients:detail", pk=patient.pk)
    if not patient.email:
        messages.error(
            request,
            "Add an email address to the patient profile before resending activation.",
        )
        return redirect("patients:detail", pk=patient.pk)

    username = _patient_username(patient)
    temporary_password = _temporary_password()
    with transaction.atomic():
        patient_user = User.objects.select_for_update().get(pk=patient.user_id)
        patient_user.set_password(temporary_password)
        # A reset credential must be treated as a first login even if the
        # patient previously signed in with an older temporary credential.
        patient_user.last_login = None
        patient_user.save(update_fields=("password", "last_login"))
        _send_patient_activation_email(patient, username, temporary_password)
        _record_patient_audit(request, "PATIENT_ACCOUNT_ACTIVATION_RESENT", patient)

    messages.success(
        request,
        f"A fresh activation email was sent to {patient.email}. Username: {username}. "
        f"Temporary password: {temporary_password}.",
    )
    return redirect("patients:detail", pk=patient.pk)


@role_required(*PATIENT_MANAGE_ROLES)
def patient_update(request: HttpRequest, pk: int) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()
            _record_patient_audit(request, "PATIENT_UPDATED", patient)
            messages.success(request, f"Patient {patient.get_full_name()} was updated.")
            return redirect("patients:detail", pk=patient.pk)
    else:
        form = PatientForm(instance=patient)

    return render(request, "patients/patient_form.html", {"form": form, "is_edit": True, "patient": patient})


@role_required(*PATIENT_MANAGE_ROLES)
def patient_deactivate(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method != "POST":
        raise PermissionDenied
    patient = get_object_or_404(Patient, pk=pk)
    patient.status = Patient.INACTIVE
    patient.save(update_fields=("status", "updated_at"))
    _record_patient_audit(request, "PATIENT_DEACTIVATED", patient)
    messages.success(request, f"Patient {patient.get_full_name()} was deactivated.")
    return redirect("patients:detail", pk=patient.pk)


@role_required(*PATIENT_MANAGE_ROLES)
def patient_archive(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method != "POST":
        raise PermissionDenied
    patient = get_object_or_404(Patient, pk=pk)
    patient.status = Patient.ARCHIVED
    patient.save(update_fields=("status", "updated_at"))
    _record_patient_audit(request, "PATIENT_ARCHIVED", patient)
    messages.success(request, f"Patient {patient.get_full_name()} was archived.")
    return redirect("patients:detail", pk=patient.pk)