"""Reusable role authorization decorators and mixins."""

from collections.abc import Callable, Collection
from functools import wraps
from typing import Any, TypeVar

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.views import View
from django.views.generic.base import ContextMixin

from .roles import ADMIN, DOCTOR, PATIENT, user_has_any_role, user_has_role

ViewCallable = TypeVar("ViewCallable", bound=Callable[..., HttpResponse])


def role_required(*roles: str) -> Callable[[ViewCallable], ViewCallable]:
    """Require an authenticated user with at least one of the supplied roles."""

    if not roles:
        raise ValueError("role_required requires at least one role")

    def decorator(view_func: ViewCallable) -> ViewCallable:
        @wraps(view_func)
        def wrapped_view(
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    settings.LOGIN_URL,
                )
            if not user_has_any_role(request.user, roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped_view  # type: ignore[return-value]

    return decorator


class RoleRequiredMixin(ContextMixin, View):
    """Class-based view mixin that enforces one of the configured roles."""

    required_roles: Collection[str] = ()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.required_roles:
            raise ValueError("RoleRequiredMixin requires required_roles")
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not user_has_any_role(request.user, self.required_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def patient_owner_required(view_func: ViewCallable) -> ViewCallable:
    """Allow clinical/admin roles or a patient viewing their own user ID.

    The Patient model does not exist until the database phase, so this
    temporary guard uses the linked Django user ID as the ownership key.
    """

    @wraps(view_func)
    def wrapped_view(
        request: HttpRequest,
        patient_user_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if user_has_any_role(request.user, (ADMIN, DOCTOR)):
            return view_func(request, patient_user_id, *args, **kwargs)
        if user_has_role(request.user, PATIENT) and request.user.pk == patient_user_id:
            return view_func(request, patient_user_id, *args, **kwargs)
        raise PermissionDenied

    return wrapped_view  # type: ignore[return-value]