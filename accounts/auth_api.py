from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserSubscription


def _active_subscription_payload(user):
    subscription = (
        UserSubscription.objects.select_related("plan")
        .filter(user_id=user.id, status__in=["active", "trial"])
        .order_by("-updated_at")
        .first()
    )
    if not subscription:
        return None
    return {
        "status": subscription.status,
        "plan_code": subscription.plan.code,
        "plan_title": subscription.plan.title,
        "ends_at": subscription.ends_at,
    }


def _user_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "reputation": getattr(getattr(user, "profile", None), "reputation", 0),
        "subscription": _active_subscription_payload(user),
    }


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        get_token(request)
        return Response({"detail": "CSRF cookie set"})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = (request.data.get("email") or request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not identifier or not password:
            return Response(
                {"detail": "Email/username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=identifier, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user, backend="accounts.auth_backends.IdentityUserBackend")
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return Response({"user": _user_payload(user)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": _user_payload(request.user)})
