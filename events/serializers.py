from rest_framework import serializers
from .models import ParsedMessage, RoadEvent, EventVote, EventMedia

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
