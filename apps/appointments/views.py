"""Views for the appointments application."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.audit_logging.models import AuditLog
from apps.authentication.permissions import role_required
from apps.authentication.roles import (
    ADMIN,
    DOCTOR,
    PATIENT,
    RECEPTIONIST,
    user_has_any_role,
    user_has_role,
)
from apps.patients.models import Patient

from .forms import AppointmentForm, AppointmentStatusForm, PatientAppointmentRequestForm
from .models import Appointment

VIEW_ROLES = (ADMIN, RECEPTIONIST, DOCTOR)
MANAGE_ROLES = (ADMIN, RECEPTIONIST)


def _record_appointment_audit(request, action: str, appointment: Appointment) -> None:
    AuditLog.objects.create(
        user=request.user,
        action=action,
        description=f"{action.replace('_', ' ').title()}: {appointment.patient.get_full_name()}",
        content_object=appointment,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


@login_required
def appointment_list(request):
    if user_has_role(request.user, PATIENT):
        patient = Patient.objects.filter(user=request.user).first()
        if patient is None:
            raise PermissionDenied
        appointments = Appointment.objects.filter(patient=patient).select_related(
            "patient",
            "doctor__staff_profile__user",
        )
    elif user_has_any_role(request.user, VIEW_ROLES):
        appointments = Appointment.objects.select_related(
            "patient",
            "doctor__staff_profile__user",
        )
    else:
        raise PermissionDenied

    pending_requests = appointments.filter(status=Appointment.REQUESTED)
    return render(
        request,
        "appointments/appointment_list.html",
        {
            "appointments": appointments,
            "pending_requests": pending_requests,
            "can_manage_appointments": user_has_any_role(request.user, MANAGE_ROLES)
            or user_has_role(request.user, DOCTOR),
        },
    )


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor__staff_profile__user"),
        pk=pk,
    )

    if user_has_role(request.user, PATIENT):
        if appointment.patient.user_id != request.user.pk:
            raise PermissionDenied
    elif not user_has_any_role(request.user, VIEW_ROLES):
        raise PermissionDenied

    return render(
        request,
        "appointments/appointment_detail.html",
        {
            "appointment": appointment,
            "status_form": AppointmentStatusForm(instance=appointment),
            "can_update_status": user_has_any_role(request.user, (ADMIN, RECEPTIONIST, DOCTOR)),
        },
    )


@role_required(RECEPTIONIST, ADMIN)
def appointment_create(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            _record_appointment_audit(request, "APPOINTMENT_CREATED", appointment)
            messages.success(request, "Appointment scheduled successfully.")
            return redirect("appointments:detail", pk=appointment.pk)
    else:
        form = AppointmentForm(initial={"status": Appointment.SCHEDULED})

    return render(request, "appointments/appointment_form.html", {"form": form, "is_edit": False})


@role_required(PATIENT)
def appointment_request(request):
    patient = Patient.objects.filter(user=request.user).first()
    if patient is None:
        patient = Patient.objects.create(
            user=request.user,
            first_name=request.user.first_name or request.user.username,
            last_name=request.user.last_name or "Patient",
            email=request.user.email or "",
        )
        messages.info(
            request,
            "Your patient profile was created automatically. You can now request an appointment.",
        )

    if request.method == "POST":
        form = PatientAppointmentRequestForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.status = Appointment.REQUESTED
            appointment.created_by = request.user
            appointment.save()
            _record_appointment_audit(request, "APPOINTMENT_REQUESTED", appointment)
            messages.success(request, "Your appointment request has been sent to reception.")
            return redirect("appointments:detail", pk=appointment.pk)
    else:
        form = PatientAppointmentRequestForm()

    return render(request, "appointments/appointment_request_form.html", {"form": form})


@login_required
def appointment_status_update(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor__staff_profile__user"),
        pk=pk,
    )

    if user_has_role(request.user, PATIENT):
        raise PermissionDenied
    if not user_has_any_role(request.user, (ADMIN, RECEPTIONIST, DOCTOR)):
        raise PermissionDenied

    if request.method == "POST":
        form = AppointmentStatusForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_appointment = form.save()
            _record_appointment_audit(
                request,
                "APPOINTMENT_STATUS_UPDATED",
                updated_appointment,
            )
            messages.success(
                request,
                f"Appointment status updated to {updated_appointment.get_status_display()}.",
            )
            return redirect("appointments:detail", pk=updated_appointment.pk)
    else:
        initial = {"status": Appointment.SCHEDULED} if appointment.status == Appointment.REQUESTED else {}
        form = AppointmentStatusForm(instance=appointment, initial=initial)

    return render(
        request,
        "appointments/appointment_detail.html",
        {
            "appointment": appointment,
            "status_form": form,
            "can_update_status": True,
        },
    )
