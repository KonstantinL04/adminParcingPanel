# serializers.py

from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.db import models as django_models
from .models import (
    EventClass,
    EventClassItem,
    MapEvent,
    EventMedia,
    EntityVote,
    PocketGisSource,
    PocketGisImport,
)


# ========== EVENT CLASSES ==========

class EventClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventClass
        fields = ["id", "name", "icon", "sort_order", "enabled"]


class EventClassItemSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="event_class.name", read_only=True)
    event_class_icon = serializers.SerializerMethodField()

    def get_event_class_icon(self, obj):
        icon = obj.event_class.icon
        if icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(icon.url)
            return icon.url
        return None

    class Meta:
        model = EventClassItem
        fields = [
            "id",
            "event_class",
            "class_name",
            "event_class_icon",
            "name",
            "icon",
            "source_kind",
            "ttl_minutes",
            "sort_order",
            "enabled",
        ]


class EventClassCatalogSerializer(serializers.ModelSerializer):
    items = EventClassItemSerializer(many=True, read_only=True)

    class Meta:
        model = EventClass
        fields = ["id", "name", "icon", "sort_order", "enabled", "items"]


# ========== MEDIA ==========

class EventMediaSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    class Meta:
        model = EventMedia
        fields = ["id", "image", "image_url", "user_id", "created_at"]


class EventMediaUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = ["image", "user_id"]

    def create(self, validated_data):
        event_id = self.context.get("event_id")
        validated_data["event_id"] = event_id
        return super().create(validated_data)


# ========== MAP EVENT ==========

class MapEventListSerializer(serializers.ModelSerializer):
    """Список точек для карты"""
    category_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    category_icon = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return getattr(obj.class_item, 'name', '') or ''

    def get_class_name(self, obj):
        return getattr(getattr(obj.class_item, "event_class", None), "name", "") or ""

    def get_category_icon(self, obj):
        icon = getattr(obj.class_item, 'icon', None)
        if icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(icon.url)
            return icon.url
        # fallback: иконка класса
        class_icon = getattr(obj.class_item, 'event_class', None)
        if class_icon and class_icon.icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(class_icon.icon.url)
        return None

    class Meta:
        model = MapEvent
        fields = [
            "id",
            "external_idx",
            "source_object_id",
            "location",
            "class_item",
            "category_name",
            "class_name",
            "category_icon",
            "source_name",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "details",
            "source",
            "source_kind",
            "status",
            "is_active",
            "confirmations",
            "denials",
            "first_seen_at",
            "last_seen_at",
        ]


class MapEventDetailSerializer(serializers.ModelSerializer):
    """Детальная информация о точке"""
    category_name = serializers.SerializerMethodField()
    media = EventMediaSerializer(many=True, read_only=True)

    def get_category_name(self, obj):
        return getattr(obj.class_item, 'name', '') or ''

    class Meta:
        model = MapEvent
        fields = [
            "id",
            "external_idx",
            "source_object_id",
            "location",
            "class_item",
            "category_name",
            "source_name",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "details",
            "is_active",
            "status",
            "source_kind",
            "confirmations",
            "denials",
            "first_seen_at",
            "last_seen_at",
            "created_at",
            "media",
        ]


class MapEventUpdateSerializer(serializers.ModelSerializer):
    """Обновление точки"""
    class_item = serializers.PrimaryKeyRelatedField(
        queryset=EventClassItem.objects.filter(enabled=True),
        required=False
    )

    class Meta:
        model = MapEvent
        fields = [
            "class_item",
            "location",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "details",
            "status",
            "is_active",
        ]


class MapEventCreateSerializer(serializers.ModelSerializer):
    """Создание точки вручную"""
    class_item = serializers.PrimaryKeyRelatedField(
        queryset=EventClassItem.objects.filter(enabled=True)
    )

    class Meta:
        model = MapEvent
        fields = [
            "class_item",
            "location",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "details",
        ]

    def create(self, validated_data):
        max_idx = MapEvent.objects.filter(
            source_kind=MapEvent.SOURCE_STATIC
        ).aggregate(django_models.Max("external_idx")).get("external_idx__max") or 0

        return MapEvent.objects.create(
            source_kind=MapEvent.SOURCE_STATIC,
            source="user",
            external_idx=max_idx + 1,
            source_object_id=f"manual-{max_idx + 1}",
            is_active=True,
            status=MapEvent.STATUS_CONFIRMED,
            **validated_data,
        )


# ========== POCKETGIS ==========

class PocketGisSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PocketGisSource
        fields = ["id", "name", "enabled", "last_sync_at", "last_status"]


class PocketGisImportSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = PocketGisImport
        fields = [
            "id",
            "source",
            "source_name",
            "file_name",
            "status",
            "rows_total",
            "rows_inserted",
            "rows_updated",
            "rows_disabled",
            "error_text",
            "created_at",
            "finished_at",
        ]


# ========== VOTES ==========

class EntityVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityVote
        fields = ["id", "event", "vote", "user_id", "created_at"]
        read_only_fields = ["event", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        lat = request.data.get("lat")
        lon = request.data.get("lon")

        if lat is not None and lon is not None:
            validated_data["voter_location"] = Point(float(lon), float(lat), srid=4326)

        return super().create(validated_data)
