from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import (
    IdentityUser,
    UserProfile,
    Role,
    UserRole,
    AuthIdentity,
    SubscriptionPlan,
    UserSubscription,
)
from .serializers import (
    IdentityUserSerializer,
    UserProfileSerializer,
    RoleSerializer,
    UserRoleSerializer,
    AuthIdentitySerializer,
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
)


class IdentityUserViewSet(ModelViewSet):
    queryset = IdentityUser.objects.all()
    serializer_class = IdentityUserSerializer
    permission_classes = [IsAuthenticated]


class UserProfileViewSet(ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.select_related("user", "role").all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated]


class AuthIdentityViewSet(ModelViewSet):
    queryset = AuthIdentity.objects.select_related("user").all()
    serializer_class = AuthIdentitySerializer
    permission_classes = [IsAuthenticated]


class SubscriptionPlanViewSet(ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]


class UserSubscriptionViewSet(ModelViewSet):
    queryset = UserSubscription.objects.select_related("user", "plan").all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
