from rest_framework.permissions import BasePermission


class IsStaffOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        )
