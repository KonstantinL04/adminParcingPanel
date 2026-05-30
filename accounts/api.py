from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .permissions import IsStaffOrSuperuser, IsSuperuser

from .models import (
    IdentityUser,
    UserProfile,
    UserReputationLog,
    ReputationRule,
    Role,
    UserRole,
    AuthIdentity,
    AppPurchase,
)
from .serializers import (
    IdentityUserSerializer,
    UserProfileSerializer,
    UserReputationLogSerializer,
    ReputationApplySerializer,
    ReputationRuleSerializer,
    RoleSerializer,
    UserRoleSerializer,
    AuthIdentitySerializer,
    AppPurchaseSerializer,
)
from .services import apply_reputation_change


class IdentityUserViewSet(ModelViewSet):
    queryset = IdentityUser.objects.all()
    serializer_class = IdentityUserSerializer
    permission_classes = [IsStaffOrSuperuser]


class UserProfileViewSet(ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsStaffOrSuperuser]

    @action(detail=False, methods=["patch"], url_path="by-user/(?P<user_id>[^/.]+)", permission_classes=[AllowAny])
    def update_by_user(self, request, user_id=None):
        profile = UserProfile.objects.filter(user_id=user_id).first()
        if not profile:
            return Response({"detail": "Profile not found"}, status=404)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserReputationLogViewSet(ModelViewSet):
    queryset = UserReputationLog.objects.select_related("user", "content_type").all()
    serializer_class = UserReputationLogSerializer
    permission_classes = [IsStaffOrSuperuser]

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    @action(detail=False, methods=["post"], url_path="apply", permission_classes=[AllowAny])
    def apply(self, request):
        serializer = ReputationApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        log = apply_reputation_change(
            user=data["user_id"],
            action=data["action"],
            delta=data.get("reputation_delta"),
            comment=data.get("comment", ""),
        )
        if not log:
            return Response({"detail": "User not found"}, status=404)
        return Response(UserReputationLogSerializer(log).data, status=201)


class ReputationRuleViewSet(ModelViewSet):
    queryset = ReputationRule.objects.all()
    serializer_class = ReputationRuleSerializer
    permission_classes = [IsStaffOrSuperuser]


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsStaffOrSuperuser]


class UserRoleViewSet(ModelViewSet):
    queryset = UserRole.objects.select_related("user", "role").all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsSuperuser]


class AuthIdentityViewSet(ModelViewSet):
    queryset = AuthIdentity.objects.select_related("user").all()
    serializer_class = AuthIdentitySerializer
    permission_classes = [IsStaffOrSuperuser]


class AppPurchaseViewSet(ModelViewSet):
    queryset = AppPurchase.objects.select_related("user").all()
    serializer_class = AppPurchaseSerializer
    permission_classes = [IsStaffOrSuperuser]
