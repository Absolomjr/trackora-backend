from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import User


class IsAdmin(BasePermission):
    """Full access — Admin / superuser only."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsManager(BasePermission):
    """Manager (or Admin) — products, stock, reports."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_manager or user.is_admin))


class IsAdminOrManager(IsManager):
    """Alias for clarity in views that allow Admin + Manager."""


class IsManagerOrReadOnly(BasePermission):
    """
    Anyone authenticated can read; only Manager/Admin can write.
    Used for inventory (products, categories, suppliers).
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_manager or user.is_admin


class IsStaffOrAbove(BasePermission):
    """
    Any authenticated role (Staff, Manager, Admin) may act.
    Used for stock in/out where Staff is allowed.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in (User.Role.STAFF, User.Role.MANAGER, User.Role.ADMIN)
        )
