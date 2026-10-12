"""Role names and server-side role helpers for MediManage."""

from collections.abc import Collection

from django.contrib.auth import get_user_model

ADMIN = "ADMIN"
RECEPTIONIST = "RECEPTIONIST"
DOCTOR = "DOCTOR"
PATIENT = "PATIENT"

ROLE_NAMES = (ADMIN, RECEPTIONIST, DOCTOR, PATIENT)
ROLE_QUERY_VALUES = {
    ADMIN: "admin",
    RECEPTIONIST: "receptionist",
    DOCTOR: "doctor",
    PATIENT: "patient",
}

User = get_user_model()


def get_user_roles(user: User) -> set[str]:
    """Return the canonical roles assigned to a user."""

    if not getattr(user, "is_authenticated", False):
        return set()

    roles = {
        group.name.upper()
        for group in user.groups.all()
        if group.name.upper() in ROLE_NAMES
    }
    if getattr(user, "is_superuser", False):
        roles.add(ADMIN)
    return roles


def user_has_any_role(user: User, roles: Collection[str]) -> bool:
    """Return whether a user has at least one of the requested roles."""

    requested_roles = {role.upper() for role in roles}
    return bool(get_user_roles(user).intersection(requested_roles))


def user_has_role(user: User, role: str) -> bool:
    """Return whether a user has one specific role."""

    return user_has_any_role(user, (role,))