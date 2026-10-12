"""URL configuration for the queue application."""

from django.urls import path

from .views import queue_add, queue_list, queue_update_status

app_name = "queue"

urlpatterns = [
    path("", queue_list, name="list"),
    path("add/", queue_add, name="add"),
    path("<int:pk>/update-status/", queue_update_status, name="update_status"),
]
