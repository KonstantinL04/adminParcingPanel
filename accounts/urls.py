from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    IdentityUserViewSet,
    UserProfileViewSet,
    UserReputationLogViewSet,
    ReputationRuleViewSet,
    RoleViewSet,
    UserRoleViewSet,
    AuthIdentityViewSet,
    AppPurchaseViewSet,
)
from .auth_api import ChangePasswordView, CsrfView, LoginView, LogoutView, MeView, MobileRegisterView

router = DefaultRouter()
router.register("users", IdentityUserViewSet, basename="accounts_users")
router.register("profiles", UserProfileViewSet, basename="accounts_profiles")
router.register("reputation", UserReputationLogViewSet, basename="accounts_reputation")
router.register("reputation-rules", ReputationRuleViewSet, basename="accounts_reputation_rules")
router.register("roles", RoleViewSet, basename="accounts_roles")
router.register("user_roles", UserRoleViewSet, basename="accounts_user_roles")
router.register("auth_identities", AuthIdentityViewSet, basename="accounts_auth_identities")
router.register("app-purchases", AppPurchaseViewSet, basename="accounts_app_purchases")

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/mobile-register/", MobileRegisterView.as_view(), name="auth-mobile-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    *router.urls,
]
