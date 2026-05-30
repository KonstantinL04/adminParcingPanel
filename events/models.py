from django.db import models
from django.contrib.gis.db import models as gis_models


class EventClass(models.Model):
    #Класс событий (группа) - например: Камеры, Засады, Опасности
    name = models.CharField(max_length=128, unique=True)
    icon = models.ImageField(upload_to="event_classes/", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class EventClassItem(models.Model):
    # Элемент класса (категория) - например: На скорость, На красный, Засада ДПС
    SOURCE_STATIC = "static"
    SOURCE_DYNAMIC = "dynamic"
    SOURCE_CHOICES = [
        (SOURCE_STATIC, "static"),
        (SOURCE_DYNAMIC, "dynamic"),
    ]

    event_class = models.ForeignKey(EventClass, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=128)
    icon = models.ImageField(upload_to="event_class_items/", null=True, blank=True)
    source_kind = models.CharField(max_length=16, choices=SOURCE_CHOICES, db_index=True)
    ttl_minutes = models.PositiveIntegerField(default=60)
    sort_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("event_class", "name")]

    def __str__(self):
        return f"{self.event_class.name} / {self.name}"


class MapEvent(models.Model):
    """Точка на карте (событие)"""
    SOURCE_STATIC = "static"
    SOURCE_DYNAMIC = "dynamic"
    SOURCE_CHOICES = [
        (SOURCE_STATIC, "static"),
        (SOURCE_DYNAMIC, "dynamic"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_CONFIRMED = "confirmed"
    STATUS_DENIED = "denied"
    STATUS_EXPIRED = "expired"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "active"),
        (STATUS_CONFIRMED, "confirmed"),
        (STATUS_DENIED, "denied"),
        (STATUS_EXPIRED, "expired"),
        (STATUS_ARCHIVED, "archived"),
    ]

    # Основное
    location = gis_models.PointField(srid=4326)
    class_item = models.ForeignKey(
        EventClassItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )

    # Параметры зоны
    speed_limit = models.IntegerField(default=0)
    dir_type = models.IntegerField(default=1)
    direction = models.IntegerField(default=0)
    distance = models.IntegerField(default=0)
    angle = models.IntegerField(default=0)

    # Мета
    details = models.TextField(blank=True, default="")
    source_kind = models.CharField(max_length=16, choices=SOURCE_CHOICES, db_index=True)
    source = models.CharField(max_length=20, default="user")  # user / telegram / import
    source_name = models.CharField(max_length=128, blank=True, default="")  # имя источника импорта
    source_object_id = models.CharField(max_length=64, blank=True, default="")
    external_idx = models.IntegerField(null=True, blank=True)

    # Статус
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_CONFIRMED, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    confirmations = models.IntegerField(default=0)
    denials = models.IntegerField(default=0)

    # Для динамических событий
    valid_until = models.DateTimeField(null=True, blank=True)
    confidence = models.FloatField(default=0.5)
    user_id = models.CharField(max_length=64, null=True, blank=True)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            gis_models.Index(fields=["source_kind", "is_active", "last_seen_at"]),
            gis_models.Index(fields=["class_item", "is_active"]),
        ]

    def __str__(self):
        name = getattr(self.class_item, 'name', '') or 'Event'
        return f"#{self.id} {name}"


class EventMedia(models.Model):
    #Фотографии события
    event = models.ForeignKey(MapEvent, on_delete=models.CASCADE, related_name="media")
    user_id = models.CharField(max_length=64)
    image = models.ImageField(upload_to="event_photos/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class EntityVote(models.Model):
    #Голосование на событие
    event = models.ForeignKey(MapEvent, on_delete=models.CASCADE, related_name="votes")
    user_id = models.CharField(max_length=64)
    voter_location = gis_models.PointField(null=True, blank=True)
    vote = models.SmallIntegerField(choices=[(1, "confirm"), (-1, "deny")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user_id")
        indexes = [
            models.Index(fields=["event"], name="events_vote_event_idx"),
            models.Index(fields=["user_id"], name="events_vote_user_idx"),
        ]


class PocketGisSource(models.Model):
    #Источник импорта PocketGIS
    name = models.CharField(max_length=128, unique=True)
    enabled = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PocketGisImport(models.Model):
    #История импортов
    source = models.ForeignKey(PocketGisSource, null=True, on_delete=models.SET_NULL, related_name="imports")
    file_name = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, default="running")
    rows_total = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_disabled = models.PositiveIntegerField(default=0)
    error_text = models.TextField(blank=True, default="")
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
