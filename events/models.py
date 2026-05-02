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


class PocketGisSource(models.Model):
    name = models.CharField(max_length=128, unique=True)
    url = models.URLField(blank=True, default="")
    enabled = models.BooleanField(default=True)
    update_interval_hours = models.PositiveIntegerField(default=24)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=32, blank=True, default="")
    etag = models.CharField(max_length=256, blank=True, default="")
    last_modified = models.CharField(max_length=256, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PocketGisCategory(models.Model):
    type_code = models.IntegerField(db_index=True)
    name = models.CharField(max_length=128)
    icon = models.ImageField(upload_to="pocketgis_categories/", null=True, blank=True)
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("type_code", "name")]

    def __str__(self):
        return f"{self.type_code}: {self.name}"


class PocketGisImport(models.Model):
    STATUS_CHOICES = [
        ("running", "running"),
        ("success", "success"),
        ("failed", "failed"),
    ]

    source = models.ForeignKey(
        PocketGisSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="imports",
    )
    file_name = models.CharField(max_length=255, blank=True, default="")
    source_date = models.CharField(max_length=128, blank=True, default="")
    file_hash = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="running")
    rows_total = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_disabled = models.PositiveIntegerField(default=0)
    error_text = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import #{self.id} ({self.status})"


class PocketGisPoint(models.Model):
    source = models.ForeignKey(
        PocketGisSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points",
    )
    last_import = models.ForeignKey(
        PocketGisImport,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points",
    )
    category = models.ForeignKey(
        PocketGisCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="points",
    )
    region = models.ForeignKey(
        "adminparcing.Region",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pocketgis_points",
    )
    city = models.ForeignKey(
        "adminparcing.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pocketgis_points",
    )

    external_idx = models.IntegerField(db_index=True)
    source_object_id = models.CharField(max_length=64, blank=True, default="")
    location = gis_models.PointField(srid=4326)

    type_code = models.IntegerField(db_index=True)
    speed_limit = models.IntegerField(default=0)
    dir_type = models.IntegerField(default=0)
    direction = models.IntegerField(default=0)
    distance = models.IntegerField(default=0)
    angle = models.IntegerField(default=0)
    details = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source", "external_idx")
        indexes = [
            gis_models.Index(fields=["region", "city", "category", "is_active"]),
            gis_models.Index(fields=["type_code"]),
            gis_models.Index(fields=["source_object_id"]),
        ]

    def __str__(self):
        return f"{self.external_idx} ({self.type_code})"
