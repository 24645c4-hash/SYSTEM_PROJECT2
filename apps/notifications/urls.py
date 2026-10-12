"""URL configuration for the notifications application."""

from django.urls import path

from .views import mark_notification_read, notification_list

app_name = "notifications"

urlpatterns = [
    path("", notification_list, name="list"),
    path("<int:pk>/read/", mark_notification_read, name="mark_read"),
]