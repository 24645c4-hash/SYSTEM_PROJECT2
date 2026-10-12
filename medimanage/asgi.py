"""ASGI config for the MediManage project."""

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medimanage.settings")

application = get_asgi_application()