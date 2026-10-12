"""Views for the notifications application."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    """Display only the notifications addressed to the logged-in user."""

    notifications = Notification.objects.filter(recipient=request.user).select_related("patient")
    return render(
        request,
        "notifications/notification_list.html",
        {"notifications": notifications},
    )


@login_required
@require_POST
def mark_notification_read(request, pk):
    """Mark a specific notification as read and redirect back to the inbox."""

    notification = get_object_or_404(Notification.objects.select_related("recipient"), pk=pk)
    if notification.recipient_id != request.user.pk:
        raise PermissionDenied

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])

    messages.success(request, "Notification marked as read.")
    return redirect("notifications:list")
