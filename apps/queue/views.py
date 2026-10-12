"""Views for the queue management application."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.appointments.models import Appointment
from apps.authentication.permissions import role_required
from apps.authentication.roles import ADMIN, DOCTOR, RECEPTIONIST, user_has_any_role

from .forms import QueueEntryForm, QueueStatusForm
from .models import QueueEntry


def _sync_appointment_status(appointment: Appointment, queue_status: str) -> None:
    if appointment is None:
        return
    if queue_status == QueueEntry.WAITING:
        appointment.status = Appointment.WAITING
    elif queue_status == QueueEntry.IN_CONSULTATION:
        appointment.status = Appointment.IN_CONSULTATION
    elif queue_status == QueueEntry.COMPLETED:
        appointment.status = Appointment.COMPLETED
    elif queue_status == QueueEntry.CANCELLED:
        appointment.status = Appointment.CANCELLED
    appointment.save(update_fields=("status", "updated_at"))


@role_required(ADMIN, RECEPTIONIST, DOCTOR)
def queue_list(request):
    entries = QueueEntry.objects.select_related("patient", "appointment").all()
    return render(
        request,
        "queue/queue_list.html",
        {
            "entries": entries,
            "can_manage_queue": user_has_any_role(request.user, (ADMIN, RECEPTIONIST)),
        },
    )


@role_required(ADMIN, RECEPTIONIST)
def queue_add(request):
    if request.method == "POST":
        form = QueueEntryForm(request.POST)
        if form.is_valid():
            queue_entry = form.save(commit=False)
            queue_entry.created_by = request.user
            queue_entry.save()
            _sync_appointment_status(queue_entry.appointment, queue_entry.status)
            messages.success(request, "Patient added to the queue.")
            return redirect("queue:list")
    else:
        form = QueueEntryForm(initial={"status": QueueEntry.WAITING})

    return render(request, "queue/queue_form.html", {"form": form})


@role_required(ADMIN, RECEPTIONIST, DOCTOR)
def queue_update_status(request, pk):
    queue_entry = get_object_or_404(QueueEntry.objects.select_related("patient", "appointment"), pk=pk)
    if request.method == "POST":
        form = QueueStatusForm(request.POST, instance=queue_entry)
        if form.is_valid():
            form.save()
            _sync_appointment_status(queue_entry.appointment, queue_entry.status)
            messages.success(request, "Queue status updated.")
            return redirect("queue:list")
    else:
        form = QueueStatusForm(instance=queue_entry)

    return render(request, "queue/queue_form.html", {"form": form, "queue_entry": queue_entry})
