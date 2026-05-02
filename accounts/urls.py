from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    IdentityUserViewSet,
    UserProfileViewSet,
    RoleViewSet,
    UserRoleViewSet,
    AuthIdentityViewSet,
    SubscriptionPlanViewSet,
    UserSubscriptionViewSet,
)
from .auth_api import CsrfView, LoginView, LogoutView, MeView

router = DefaultRouter()
router.register("users", IdentityUserViewSet, basename="accounts_users")
router.register("profiles", UserProfileViewSet, basename="accounts_profiles")
router.register("roles", RoleViewSet, basename="accounts_roles")
router.register("user_roles", UserRoleViewSet, basename="accounts_user_roles")
router.register("auth_identities", AuthIdentityViewSet, basename="accounts_auth_identities")
router.register("plans", SubscriptionPlanViewSet, basename="accounts_subscription_plans")
router.register("user_subscriptions", UserSubscriptionViewSet, basename="accounts_user_subscriptions")

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    *router.urls,
]
