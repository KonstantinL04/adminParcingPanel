from django.db import models
from django.contrib.gis.db import models as gis_models

# Create your models here.
class ParsedMessage(models.Model):
    telegram_message_id = models.BigIntegerField()
    chat = models.ForeignKey(
        "adminparcing.Chat",
        on_delete=models.PROTECT,
        related_name="parsed_messages"
    )

    author_id = models.BigIntegerField(null=True, blank=True)
    author_name = models.CharField(max_length=255, blank=True)

    text = models.TextField()

    category = models.ForeignKey(
        "adminparcing.AlertCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="parsed_messages"
    )

    created_at = models.DateTimeField()
    parsed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["category"]),
            models.Index(fields=["chat"]),
        ]

class RoadEvent(models.Model):
    source_message = models.ForeignKey(
        ParsedMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    location = gis_models.PointField()

    category_id = models.IntegerField(db_index=True)
    category_code = models.CharField(max_length=50)
    category_label = models.CharField(max_length=100)

    extra_params = models.JSONField(null=True, blank=True)
    comment = models.TextField(blank=True)
    user_id = models.CharField(max_length=64, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=[
            ("active", "active"),
            ("confirmed", "confirmed"),
            ("denied", "denied"),
            ("expired", "expired"),
        ],
        default="active"
    )

    confidence = models.FloatField(default=0.5)
    confirmations = models.IntegerField(default=0)

    valid_until = models.DateTimeField(null=True, blank=True)

    source = models.CharField(
        max_length=20,
        choices=[("user", "user"), ("telegram", "telegram")]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

class EventVote(models.Model):
    event = models.ForeignKey(RoadEvent, related_name="votes", on_delete=models.CASCADE)
    user_id = models.CharField(max_length=64)
    voter_location = gis_models.PointField()
    vote = models.SmallIntegerField(choices=[(1, "confirm"), (-1, "deny")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user_id")

class EventMedia(models.Model):
    event = models.ForeignKey(
        RoadEvent,
        related_name="media",
        on_delete=models.CASCADE
    )

    user_id = models.CharField(max_length=64)
    image = models.ImageField(upload_to="event_photos/")
    created_at = models.DateTimeField(auto_now_add=True)
