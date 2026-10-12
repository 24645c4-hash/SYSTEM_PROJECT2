"""Create the canonical MediManage role groups."""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.authentication.roles import ROLE_NAMES


class Command(BaseCommand):
    help = "Create the four canonical MediManage role groups."

    def handle(self, *args, **options):
        for role_name in ROLE_NAMES:
            group, created = Group.objects.get_or_create(name=role_name)
            action = "Created" if created else "Verified"
            self.stdout.write(f"{action} role group: {group.name}")