from rest_framework import serializers
from .models import (
    ParsedMessage,
    RoadEvent,
    EventVote,
    EventMedia,
    PocketGisSource,
    PocketGisImport,
    PocketGisPoint,
    PocketGisCategory,
)

class ParsedMessageSerializer(serializers.ModelSerializer):
    chat_title = serializers.CharField(source="chat.title", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ParsedMessage
        fields = [
            "id",
            "telegram_message_id",
            "chat",
            "chat_title",
            "author_id",
            "author_name",
            "text",
            "category",
            "category_name",
            "created_at",
            "parsed_at",
        ]

class EventMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = ["id", "image", "user_id", "created_at"]

class EventVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventVote
        fields = ["id", "vote", "user_id", "created_at"]

class RoadEventSerializer(serializers.ModelSerializer):
    votes = EventVoteSerializer(many=True, read_only=True)
    media = EventMediaSerializer(many=True, read_only=True)

    class Meta:
        model = RoadEvent
        fields = [
            "id",
            "source_message",
            "location",
            "category_id",
            "category_code",
            "category_label",
            "extra_params",
            "comment",
            "user_id",
            "status",
            "source",
            "confidence",
            "confirmations",
            "valid_until",
            "created_at",
            "last_activity_at",
            "votes",
            "media",
        ]

class RoadEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadEvent
        fields = [
            "location",
            "category_id",
            "category_code",
            "category_label",
            "extra_params",
            "comment",
        ]

    def create(self, validated_data):
        request = self.context["request"]

        return RoadEvent.objects.create(
            **validated_data,
            status="active",
            source="user",
            user_id=str(request.user.id) if request.user.is_authenticated else None,
            confidence=0.6,
            confirmations=1,
        )


class PocketGisSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PocketGisSource
        fields = [
            "id",
            "name",
            "url",
            "enabled",
            "update_interval_hours",
            "last_sync_at",
            "last_status",
            "created_at",
            "updated_at",
        ]


class PocketGisCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PocketGisCategory
        fields = ["id", "type_code", "name", "icon", "enabled", "sort_order"]


class PocketGisImportSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = PocketGisImport
        fields = [
            "id",
            "source",
            "source_name",
            "file_name",
            "source_date",
            "file_hash",
            "status",
            "rows_total",
            "rows_inserted",
            "rows_updated",
            "rows_disabled",
            "error_text",
            "started_at",
            "finished_at",
            "created_at",
        ]


class PocketGisPointSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_icon = serializers.ImageField(source="category.icon", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = PocketGisPoint
        fields = [
            "id",
            "external_idx",
            "source_object_id",
            "location",
            "type_code",
            "category",
            "category_name",
            "category_icon",
            "source",
            "source_name",
            "region",
            "region_name",
            "city",
            "city_name",
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
