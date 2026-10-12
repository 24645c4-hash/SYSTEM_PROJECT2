"""WSGI config for the MediManage project."""

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medimanage.settings")

application = get_wsgi_application()