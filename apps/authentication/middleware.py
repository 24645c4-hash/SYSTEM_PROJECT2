"""Authentication middleware for temporary-password accounts."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from .roles import ADMIN, user_has_role

class FirstLoginPasswordChangeMiddleware:
    """Keep first-login users on the password-change flow until completion."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        must_change_password = request.session.get("medimanage_must_change_password")
        allowed_paths = (
            "/auth/password-change/",
            "/auth/logout/",
            "/static/",
            "/media/",
        )

        if request.user.is_authenticated and must_change_password and not request.path.startswith(
            allowed_paths
        ):
            return redirect("authentication:password_change")

        return self.get_response(request)


class AdministratorAreaAuthorizationMiddleware:
    """Prevent non-administrators from opening Django admin URLs."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            request.path.startswith("/admin/")
            and request.user.is_authenticated
            and not user_has_role(request.user, ADMIN)
        ):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        return self.get_response(request)