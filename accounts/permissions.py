from rest_framework.permissions import BasePermission


def _role_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.roles.select_related("role").values_list("role__name", flat=True))


class IsStaffOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
                or "admin" in _role_names(user)
            )
        )


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or "admin" in _role_names(user))
        )
