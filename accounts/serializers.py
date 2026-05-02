from rest_framework import serializers
from .models import (
    IdentityUser,
    UserProfile,
    Role,
    UserRole,
    AuthIdentity,
    SubscriptionPlan,
    UserSubscription,
)


class IdentityUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityUser
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = "__all__"


class AuthIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthIdentity
        fields = "__all__"


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = "__all__"


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = "__all__"
