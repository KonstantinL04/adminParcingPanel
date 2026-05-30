from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AppPurchase, AuthIdentity, IdentityUser, UserProfile


def _app_purchase_payload(user):
    purchase = (
        AppPurchase.objects
        .filter(user_id=user.id, verification_status=AppPurchase.STATUS_VERIFIED, grants_full_access=True)
        .order_by("-updated_at")
        .first()
    )
    if not purchase:
        return None
    return {
        "status": purchase.verification_status,
        "platform": purchase.platform,
        "product_id": purchase.product_id,
        "transaction_id": purchase.transaction_id,
        "grants_full_access": purchase.grants_full_access,
        "verified_at": purchase.verified_at,
    }


def _user_payload(user):
    roles = list(
        user.roles.select_related("role").values_list("role__name", flat=True)
    ) if getattr(user, "id", None) else []
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "roles": roles,
        "reputation": getattr(getattr(user, "profile", None), "reputation", 0),
        "purchase": _app_purchase_payload(user),
    }


def _generate_mobile_username(email):
    prefix = (email.split("@", 1)[0] or "user").lower()
    safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in ("_", "-"))[:20] or "user"
    username = f"{safe_prefix}_{get_random_string(6).lower()}"
    while IdentityUser.objects.filter(username__iexact=username).exists():
        username = f"{safe_prefix}_{get_random_string(6).lower()}"
    return username


class MobileRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.strip().lower()
        if IdentityUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с такой почтой уже зарегистрирован")
        return email


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль указан неверно")
        return value


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        get_token(request)
        return Response({"detail": "CSRF cookie set"})


class MobileRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MobileRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        username = _generate_mobile_username(email)
        password = get_random_string(12)

        subject = "Дорожный помощник: данные для входа"
        message = (
            "Здравствуйте!\n\n"
            "Для вас создан аккаунт в мобильном приложении «Дорожный помощник».\n\n"
            f"Логин: {username}\n"
            f"Email: {email}\n"
            f"Пароль: {password}\n\n"
            "После первого входа рекомендуем изменить пароль и заполнить профиль."
        )

        try:
            with transaction.atomic():
                user = IdentityUser(
                    email=email,
                    username=username,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
                user.set_password(password)
                user.save()
                UserProfile.objects.get_or_create(user=user, defaults={"nickname": username})
                AuthIdentity.objects.get_or_create(
                    provider="email",
                    provider_user_id=email,
                    defaults={"user": user, "email": email},
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        except Exception as exc:
            return Response({
                "detail": "Не удалось отправить письмо с данными для входа",
                "error": str(exc),
            }, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "detail": "Аккаунт создан, данные для входа отправлены на почту",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        }, status=status.HTTP_201_CREATED)


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


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password_hash"])
        return Response({"detail": "Пароль изменен"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": _user_payload(request.user)})
