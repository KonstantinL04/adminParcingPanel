from django.contrib.gis.db import models as gis_models
from django.db import models


class HelpRequest(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_WAITING_CONFIRMATION = "waiting_confirmation"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "active"),
        (STATUS_IN_PROGRESS, "in_progress"),
        (STATUS_WAITING_CONFIRMATION, "waiting_confirmation"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_CANCELED, "canceled"),
        (STATUS_EXPIRED, "expired"),
    ]

    event_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    creator_user_id = models.CharField(max_length=64, db_index=True)
    creator_location = gis_models.PointField(srid=4326, null=True, blank=True)
    search_radius_m = models.PositiveIntegerField(default=3000)
    description = models.TextField(blank=True, default="")
    selected_response = models.ForeignKey(
        "assistance.HelpRequestResponse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="selected_for_requests",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    auto_archive_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            gis_models.Index(fields=["status", "created_at"]),
            gis_models.Index(fields=["creator_user_id", "status"]),
        ]


class HelpRequestResponse(models.Model):
    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name="responses")
    responder_user_id = models.CharField(max_length=64, db_index=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    helper_arrived_at = models.DateTimeField(null=True, blank=True)
    helper_completed_at = models.DateTimeField(null=True, blank=True)
    eta_minutes = models.PositiveIntegerField(null=True, blank=True)
    chat_room_id = models.CharField(max_length=64, blank=True, null=True)
    message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("help_request", "responder_user_id")
        indexes = [
            models.Index(fields=["help_request", "accepted", "created_at"]),
        ]


class HelperPresence(models.Model):
    user_id = models.CharField(max_length=64, unique=True, db_index=True)
    location = gis_models.PointField(srid=4326)
    is_available = models.BooleanField(default=True, db_index=True)
    reliability_score = models.FloatField(default=0.0)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            gis_models.Index(fields=["is_available", "last_seen_at"]),
        ]


class HelpRequestCandidate(models.Model):
    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name="candidates")
    user_id = models.CharField(max_length=64, db_index=True)
    distance_m = models.PositiveIntegerField(default=0)
    notified_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("help_request", "user_id")
        indexes = [
            models.Index(fields=["help_request", "distance_m"]),
            models.Index(fields=["user_id", "notified_at"]),
        ]


class HelpRequestChatRoom(models.Model):
    help_request = models.OneToOneField(HelpRequest, on_delete=models.CASCADE, related_name="chat_room")
    creator_user_id = models.CharField(max_length=64, db_index=True)
    helper_user_id = models.CharField(max_length=64, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["creator_user_id", "helper_user_id", "is_active"]),
        ]


class HelpRequestChatMessage(models.Model):
    room = models.ForeignKey(HelpRequestChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender_user_id = models.CharField(max_length=64, db_index=True)
    text = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="help_chat_attachments/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["sender_user_id", "created_at"]),
        ]


class HelpRequestResolution(models.Model):
    help_request = models.OneToOneField(HelpRequest, on_delete=models.CASCADE, related_name="resolution")
    helper_user_id = models.CharField(max_length=64, db_index=True)
    solved = models.BooleanField(default=True)
    rating_delta = models.SmallIntegerField(default=0)
    rating_comment = models.CharField(max_length=255, blank=True, default="")
    resolved_by_user_id = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
