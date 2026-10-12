"""Views for the reports application."""

from django.shortcuts import render

from apps.appointments.models import Appointment
from apps.audit_logging.models import AuditLog
from apps.authentication.permissions import role_required
from apps.authentication.roles import ADMIN
from apps.patients.models import Patient
from apps.queue.models import QueueEntry


@role_required(ADMIN)
def report_dashboard(request):
    """Show a concise clinic overview for administrators and managers."""

    patient_total = Patient.objects.count()
    appointment_total = Appointment.objects.count()
    waiting_total = QueueEntry.objects.filter(status=QueueEntry.WAITING).count()
    recent_activity = AuditLog.objects.select_related("user").order_by("-created_at")[:10]

    return render(
        request,
        "reports/report_dashboard.html",
        {
            "patient_total": patient_total,
            "appointment_total": appointment_total,
            "waiting_total": waiting_total,
            "recent_activity": recent_activity,
        },
    )
