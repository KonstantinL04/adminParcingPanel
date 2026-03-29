from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from .models import IdentityUser, UserProfile, Role, UserRole, AuthIdentity
from .serializers import (
    IdentityUserSerializer,
    UserProfileSerializer,
    RoleSerializer,
    UserRoleSerializer,
    AuthIdentitySerializer,
)

class IdentityUserViewSet(ModelViewSet):
    queryset = IdentityUser.objects.all()
    serializer_class = IdentityUserSerializer
    permission_classes = [AllowAny]

class UserProfileViewSet(ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]

class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [AllowAny]

class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.select_related("user", "role").all()
    serializer_class = UserRoleSerializer
    permission_classes = [AllowAny]

class AuthIdentityViewSet(ModelViewSet):
    queryset = AuthIdentity.objects.select_related("user").all()
    serializer_class = AuthIdentitySerializer
    permission_classes = [AllowAny]
