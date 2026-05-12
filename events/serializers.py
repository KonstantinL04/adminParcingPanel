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
    HelpRequest,
    HelpRequestResponse,
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
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "ttl_minutes",
            "supports_direction",
            "supports_speed_limit",
            "supports_distance",
            "supports_angle",
            "supports_zone_render",
            "details_template",
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
    category_icon = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return getattr(obj.class_item, 'name', '') or ''

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
            "category_icon",
            "source_name",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
            "details",
            "is_active",
            "first_seen_at",
            "last_seen_at",
        ]


class MapEventDetailSerializer(serializers.ModelSerializer):
    """Детальная информация о точке"""
    category_name = serializers.SerializerMethodField()
    media = EventMediaSerializer(many=True, read_only=True)
    has_help_request = serializers.SerializerMethodField()
    help_request_status = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return getattr(obj.class_item, 'name', '') or ''

    def get_has_help_request(self, obj):
        return hasattr(obj, 'help_request')

    def get_help_request_status(self, obj):
        hr = getattr(obj, 'help_request', None)
        return hr.status if hr else None

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
            "has_help_request",
            "help_request_status",
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
        ]


class MapEventCreateSerializer(serializers.ModelSerializer):
    """Создание точки вручную"""
    class_item = serializers.PrimaryKeyRelatedField(
        queryset=EventClassItem.objects.filter(enabled=True)
    )
    is_help_request = serializers.BooleanField(default=False, write_only=True)

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
            "is_help_request",
        ]

    def create(self, validated_data):
        is_help_request = validated_data.pop("is_help_request", False)

        max_idx = MapEvent.objects.filter(
            source_kind=MapEvent.SOURCE_STATIC
        ).aggregate(django_models.Max("external_idx")).get("external_idx__max") or 0

        event = MapEvent.objects.create(
            source_kind=MapEvent.SOURCE_DYNAMIC if is_help_request else MapEvent.SOURCE_STATIC,
            source="user",
            external_idx=max_idx + 1 if not is_help_request else None,
            source_object_id=f"manual-{max_idx + 1}" if not is_help_request else "",
            is_active=True,
            status=MapEvent.STATUS_CONFIRMED if not is_help_request else MapEvent.STATUS_ACTIVE,
            **validated_data,
        )

        # Если это запрос помощи — создаем HelpRequest
        if is_help_request:
            from django.utils import timezone
            from datetime import timedelta

            class_item = validated_data.get("class_item")
            ttl = getattr(class_item, 'ttl_minutes', 120)

            HelpRequest.objects.create(
                event=event,
                creator_user_id=self.context["request"].user.id if self.context["request"].user.is_authenticated else "anonymous",
                auto_archive_at=timezone.now() + timedelta(minutes=ttl),
            )

        return event


# ========== HELP REQUEST ==========

class HelpRequestResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequestResponse
        fields = [
            "id",
            "responder_user_id",
            "accepted",
            "chat_room_id",
            "message",
            "created_at",
        ]
        read_only_fields = ["accepted", "chat_room_id", "created_at"]


class HelpRequestSerializer(serializers.ModelSerializer):
    """Запрос помощи с откликами"""
    responses = HelpRequestResponseSerializer(many=True, read_only=True)
    event_details = serializers.CharField(source="event.details", read_only=True)
    event_location = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()

    def get_event_location(self, obj):
        return {
            "type": "Point",
            "coordinates": [obj.event.location.x, obj.event.location.y],
        }

    def get_responses_count(self, obj):
        return obj.responses.count()

    class Meta:
        model = HelpRequest
        fields = [
            "id",
            "event",
            "event_details",
            "event_location",
            "creator_user_id",
            "status",
            "auto_archive_at",
            "closed_at",
            "created_at",
            "responses",
            "responses_count",
        ]


class HelpRequestRespondSerializer(serializers.Serializer):
    """Отклик на запрос помощи"""
    user_id = serializers.CharField()
    message = serializers.CharField(required=False, allow_blank=True, default="")


class HelpRequestAcceptSerializer(serializers.Serializer):
    """Принятие отклика"""
    response_id = serializers.IntegerField()


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
        fields = ["id", "vote", "user_id", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        lat = request.data.get("lat")
        lon = request.data.get("lon")

        if lat is not None and lon is not None:
            validated_data["voter_location"] = Point(float(lon), float(lat), srid=4326)

        return super().create(validated_data)