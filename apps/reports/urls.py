"""URL configuration for the reports application."""

from django.urls import path

from .views import report_dashboard

app_name = "reports"

urlpatterns = [
    path("", report_dashboard, name="dashboard"),
]