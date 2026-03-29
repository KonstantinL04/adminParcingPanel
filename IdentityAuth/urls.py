from rest_framework.routers import DefaultRouter
from .api import IdentityUserViewSet, UserProfileViewSet, RoleViewSet, UserRoleViewSet, AuthIdentityViewSet

router = DefaultRouter()
router.register("users", IdentityUserViewSet, basename="identity_users")
router.register("profiles", UserProfileViewSet, basename="user_profiles")
router.register("roles", RoleViewSet, basename="roles")
router.register("user_roles", UserRoleViewSet, basename="user_roles")
router.register("auth_identities", AuthIdentityViewSet, basename="auth_identities")

urlpatterns = router.urls
