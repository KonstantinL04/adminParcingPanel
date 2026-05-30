from django.utils import timezone
from rest_framework import serializers
from .models import NotificationTemplate, DeviceToken, NotificationJob, NotificationDelivery


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "code", "title_template", "body_template", "enabled", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "user_id", "token", "platform", "enabled", "last_seen_at", "created_at"]
        read_only_fields = ["last_seen_at", "created_at"]


class NotificationDeliverySerializer(serializers.ModelSerializer):
    device_platform = serializers.CharField(source="device.platform", read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = [
            "id",
            "job",
            "device",
            "device_platform",
            "user_id",
            "token",
            "channel",
            "status",
            "provider",
            "provider_message_id",
            "error_text",
            "attempts",
            "sent_at",
            "created_at",
            "updated_at",
        ]


class NotificationJobSerializer(serializers.ModelSerializer):
    deliveries = NotificationDeliverySerializer(many=True, read_only=True)
    template_code = serializers.CharField(source="template.code", read_only=True)

    class Meta:
        model = NotificationJob
        fields = [
            "id",
            "source_service",
            "template",
            "template_code",
            "title",
            "body",
            "payload",
            "recipients",
            "status",
            "total",
            "success",
            "failed",
            "scheduled_at",
            "started_at",
            "finished_at",
            "created_by_user_id",
            "created_at",
            "updated_at",
            "deliveries",
        ]
        read_only_fields = [
            "status",
            "total",
            "success",
            "failed",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]


class NotificationSendSerializer(serializers.Serializer):
    source_service = serializers.CharField(required=False, allow_blank=True, default="")
    template_code = serializers.CharField(required=False, allow_blank=True, default="")
    title = serializers.CharField(required=False, allow_blank=True, default="")
    body = serializers.CharField(required=False, allow_blank=True, default="")
    payload = serializers.JSONField(required=False)
    recipients = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    scheduled_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if not attrs.get("template_code") and not attrs.get("title"):
            raise serializers.ValidationError("title or template_code is required")
        if not attrs.get("template_code") and not attrs.get("body"):
            raise serializers.ValidationError("body or template_code is required")
        if "scheduled_at" in attrs and attrs["scheduled_at"] < timezone.now():
            raise serializers.ValidationError("scheduled_at must be in the future")
        return attrs
