"""URL configuration for the MediManage project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.authentication.views import setup_view


urlpatterns = [
    path("", setup_view, name="setup"),
    path("admin/", admin.site.urls),
    path("auth/", include("apps.authentication.urls")),
    path("patients/", include("apps.patients.urls")),
    path("appointments/", include("apps.appointments.urls")),
    path("queue/", include("apps.queue.urls")),
    path("medical-records/", include("apps.medical_records.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("reports/", include("apps.reports.urls")),
    path("audit/", include("apps.audit_logging.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)