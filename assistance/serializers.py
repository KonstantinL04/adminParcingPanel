from rest_framework import serializers

from .models import (
    HelpRequest,
    HelpRequestCandidate,
    HelpRequestChatMessage,
    HelpRequestChatRoom,
    HelpRequestResolution,
    HelpRequestResponse,
    HelperPresence,
)


class HelpRequestResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequestResponse
        fields = [
            "id",
            "responder_user_id",
            "accepted",
            "accepted_at",
            "helper_arrived_at",
            "helper_completed_at",
            "eta_minutes",
            "chat_room_id",
            "message",
            "created_at",
        ]
        read_only_fields = ["accepted", "accepted_at", "chat_room_id", "created_at"]


class HelpRequestSerializer(serializers.ModelSerializer):
    responses = HelpRequestResponseSerializer(many=True, read_only=True)
    event = serializers.IntegerField(source="event_id", read_only=True)
    event_details = serializers.CharField(source="description", read_only=True)
    event_location = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()
    selected_response_id = serializers.IntegerField(read_only=True)

    def get_event_location(self, obj):
        if not obj.creator_location:
            return None
        return {
            "type": "Point",
            "coordinates": [obj.creator_location.x, obj.creator_location.y],
        }

    def get_responses_count(self, obj):
        return obj.responses.count()

    class Meta:
        model = HelpRequest
        fields = [
            "id",
            "event",
            "event_id",
            "event_details",
            "event_location",
            "description",
            "creator_user_id",
            "creator_location",
            "status",
            "search_radius_m",
            "selected_response_id",
            "auto_archive_at",
            "closed_at",
            "created_at",
            "updated_at",
            "responses",
            "responses_count",
        ]
        read_only_fields = ["event_id", "created_at", "updated_at"]


class HelpRequestRespondSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    message = serializers.CharField(required=False, allow_blank=True, default="")
    eta_minutes = serializers.IntegerField(required=False, min_value=0)
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)


class HelpRequestAcceptSerializer(serializers.Serializer):
    response_id = serializers.IntegerField()


class HelpRequestCompleteSerializer(serializers.Serializer):
    solved = serializers.BooleanField()
    rating_delta = serializers.IntegerField(required=False)
    rating_comment = serializers.CharField(required=False, allow_blank=True, default="")
    helper_user_id = serializers.CharField(required=False, allow_blank=True, default="")
    resolved_by_user_id = serializers.CharField()


class HelperPresenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelperPresence
        fields = ["id", "user_id", "location", "is_available", "reliability_score", "last_seen_at", "created_at"]
        read_only_fields = ["last_seen_at", "created_at"]


class HelpRequestCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequestCandidate
        fields = ["id", "help_request", "user_id", "distance_m", "notified_at", "viewed_at", "dismissed_at"]


class HelpRequestChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequestChatMessage
        fields = ["id", "room", "sender_user_id", "text", "attachment", "created_at", "read_at"]
        read_only_fields = ["created_at", "read_at"]


class HelpRequestChatRoomSerializer(serializers.ModelSerializer):
    messages = HelpRequestChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = HelpRequestChatRoom
        fields = [
            "id",
            "help_request",
            "creator_user_id",
            "helper_user_id",
            "is_active",
            "created_at",
            "closed_at",
            "messages",
        ]


class HelpRequestResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequestResolution
        fields = [
            "id",
            "help_request",
            "helper_user_id",
            "solved",
            "rating_delta",
            "rating_comment",
            "resolved_by_user_id",
            "created_at",
        ]
        read_only_fields = ["created_at"]
