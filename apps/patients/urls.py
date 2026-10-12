"""URL configuration for the patients application."""

from django.urls import path

from .views import (
    patient_archive,
    patient_activate_account,
    patient_create,
    patient_deactivate,
    patient_detail,
    patient_dashboard,
    patient_list,
    patient_resend_activation,
    patient_update,
)

app_name = "patients"

urlpatterns = [
    path("", patient_list, name="list"),
    path("dashboard/", patient_dashboard, name="dashboard"),
    path("register/", patient_create, name="create"),
    path("<int:pk>/", patient_detail, name="detail"),
    path(
        "<int:pk>/activate-account/",
        patient_activate_account,
        name="activate_account",
    ),
    path(
        "<int:pk>/resend-activation/",
        patient_resend_activation,
        name="resend_activation",
    ),
    path("<int:pk>/edit/", patient_update, name="update"),
    path("<int:pk>/deactivate/", patient_deactivate, name="deactivate"),
    path("<int:pk>/archive/", patient_archive, name="archive"),
]