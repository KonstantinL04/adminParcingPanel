from django.db import models


class NotificationTemplate(models.Model):
    code = models.CharField(max_length=64, unique=True)
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]


class DeviceToken(models.Model):
    PLATFORM_IOS = "ios"
    PLATFORM_ANDROID = "android"
    PLATFORM_WEB = "web"
    PLATFORM_CHOICES = [
        (PLATFORM_IOS, "ios"),
        (PLATFORM_ANDROID, "android"),
        (PLATFORM_WEB, "web"),
    ]

    user_id = models.PositiveIntegerField(db_index=True)
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=16, choices=PLATFORM_CHOICES)
    enabled = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["user_id", "enabled"]),
        ]


class NotificationJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_PROCESSING, "processing"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_FAILED, "failed"),
    ]

    source_service = models.CharField(max_length=64, blank=True, default="")
    template = models.ForeignKey(NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    recipients = models.JSONField(default=list, blank=True)  # list[int]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    total = models.PositiveIntegerField(default=0)
    success = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class NotificationDelivery(models.Model):
    CHANNEL_PUSH = "push"
    CHANNEL_INAPP = "inapp"
    CHANNEL_CHOICES = [
        (CHANNEL_PUSH, "push"),
        (CHANNEL_INAPP, "inapp"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_SENT, "sent"),
        (STATUS_FAILED, "failed"),
    ]

    job = models.ForeignKey(NotificationJob, on_delete=models.CASCADE, related_name="deliveries")
    device = models.ForeignKey(
        DeviceToken,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    user_id = models.PositiveIntegerField(db_index=True)
    token = models.CharField(max_length=512, blank=True, default="")
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default=CHANNEL_PUSH)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    provider = models.CharField(max_length=32, blank=True, default="")  # fcm/apns/mock
    provider_message_id = models.CharField(max_length=128, blank=True, default="")
    error_text = models.TextField(blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["device", "status"]),
            models.Index(fields=["user_id", "status"]),
        ]
