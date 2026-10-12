"""URL configuration for the audit logging application."""

from django.urls import path

from .views import audit_log_list

app_name = "audit_logging"

urlpatterns = [
    path("", audit_log_list, name="list"),
]