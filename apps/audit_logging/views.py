"""Views for the audit logging application."""

from django.shortcuts import render

from apps.authentication.permissions import role_required
from apps.authentication.roles import ADMIN

from .models import AuditLog


@role_required(ADMIN)
def audit_log_list(request):
    """Display an immutable audit trail for the clinic."""

    logs = AuditLog.objects.select_related("user", "content_type").order_by("-created_at")
    return render(
        request,
        "audit_logging/audit_log_list.html",
        {"logs": logs},
    )
