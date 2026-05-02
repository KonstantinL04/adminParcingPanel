from django.contrib.auth.backends import BaseBackend

from .models import IdentityUser


class IdentityUserBackend(BaseBackend):
    """
    Session auth backend for existing accounts.IdentityUser table.
    Allows login by email or username.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identifier = email or username
        if not identifier or not password:
            return None

        user = (
            IdentityUser.objects.filter(email__iexact=identifier).first()
            or IdentityUser.objects.filter(username__iexact=identifier).first()
        )
        if not user or not user.is_active:
            return None

        # Support both Django-hashed and legacy plain-text values.
        if user.check_password(password) or user.password_hash == password:
            return user
        return None

    def get_user(self, user_id):
        try:
            return IdentityUser.objects.get(pk=user_id)
        except IdentityUser.DoesNotExist:
            return None
