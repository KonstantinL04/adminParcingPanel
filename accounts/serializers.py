from rest_framework import serializers
from django.utils.crypto import get_random_string
from .models import (
    IdentityUser,
    UserProfile,
    Role,
    UserRole,
    UserReputationLog,
    ReputationRule,
    AuthIdentity,
    AppPurchase,
)


class IdentityUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    roles = serializers.SerializerMethodField()
    profile_status = serializers.CharField(source="profile.status", read_only=True)
    reputation = serializers.IntegerField(source="profile.reputation", read_only=True)

    def get_roles(self, obj):
        return list(obj.roles.select_related("role").values_list("role__name", flat=True))

    class Meta:
        model = IdentityUser
        fields = [
            "id",
            "email",
            "username",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
            "roles",
            "profile_status",
            "reputation",
        ]
        read_only_fields = ["last_login", "date_joined", "roles", "profile_status", "reputation"]

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        user = IdentityUser(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password(get_random_string(32))
        user.save()
        UserProfile.objects.get_or_create(user=user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        UserProfile.objects.get_or_create(user=instance)
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"


class UserReputationLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    source_type = serializers.SerializerMethodField()

    def get_source_type(self, obj):
        return obj.content_type.model if obj.content_type else ""

    class Meta:
        model = UserReputationLog
        fields = [
            "id",
            "user",
            "user_email",
            "action",
            "reputation_delta",
            "total_reputation",
            "comment",
            "source_type",
            "object_id",
            "created_at",
        ]
        read_only_fields = ["total_reputation", "created_at", "source_type"]


class ReputationApplySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=UserReputationLog.ACTION_CHOICES)
    reputation_delta = serializers.IntegerField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReputationRuleSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = ReputationRule
        fields = [
            "id",
            "action",
            "action_label",
            "title",
            "reputation_delta",
            "description",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "action_label"]


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


class AppPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppPurchase
        fields = "__all__"
