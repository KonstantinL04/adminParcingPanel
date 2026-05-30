from django.contrib import admin
from .models import NotificationTemplate, DeviceToken, NotificationJob, NotificationDelivery


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "enabled", "updated_at"]
    search_fields = ["code", "title_template"]
    list_filter = ["enabled"]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["id", "user_id", "platform", "enabled", "last_seen_at"]
    search_fields = ["user_id", "token"]
    list_filter = ["platform", "enabled"]


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ["id", "source_service", "status", "total", "success", "failed", "created_at"]
    search_fields = ["source_service", "title", "created_by_user_id"]
    list_filter = ["status"]


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "device", "user_id", "status", "provider", "attempts", "sent_at"]
    search_fields = ["user_id", "token", "provider_message_id"]
    list_filter = ["status", "channel", "provider", "device__platform"]
