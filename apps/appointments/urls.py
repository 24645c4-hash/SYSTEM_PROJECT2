"""URL configuration for the appointments application."""

from django.urls import path

from .views import (
    appointment_create,
    appointment_detail,
    appointment_list,
    appointment_request,
    appointment_status_update,
)

app_name = "appointments"

urlpatterns = [
    path("", appointment_list, name="list"),
    path("request/", appointment_request, name="request"),
    path("create/", appointment_create, name="create"),
    path("<int:pk>/", appointment_detail, name="detail"),
    path("<int:pk>/status/", appointment_status_update, name="status_update"),
]