from rest_framework.permissions import BasePermission


def _has_moderation_access(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    role_names = set(
        user.roles.select_related("role").values_list("role__name", flat=True)
    )
    return "moderator" in role_names or "admin" in role_names


class IsModeratorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return _has_moderation_access(request.user)
