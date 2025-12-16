from rest_framework import serializers
from .models import ParsedMessage, MessageLocation, MessageRouteMatch
from rest_framework_gis.serializers import GeoFeatureModelSerializer

class MessageLocationSerializer(GeoFeatureModelSerializer):
    telegram_message_id = serializers.IntegerField(
        source="message.telegram_message_id",
        read_only=True
    )
    author_name = serializers.CharField(
        source="message.author_name",
        read_only=True
    )

    class Meta:
        model = MessageLocation
        geo_field = "location"
        fields = (
            "id",
            "telegram_message_id",
            "author_name",
            "place_name",
            "source",
            "confidence",
        )
    


class MessageRouteMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageRouteMatch
        fields = "__all__"


class ParsedMessageSerializer(serializers.ModelSerializer):
    locations = MessageLocationSerializer(many=True, required=False)
    routes = MessageRouteMatchSerializer(many=True, required=False)

    class Meta:
        model = ParsedMessage
        fields = "__all__"

    def create(self, validated_data):
        locations = validated_data.pop("locations", [])
        routes = validated_data.pop("routes", [])

        msg = ParsedMessage.objects.create(**validated_data)

        for loc in locations:
            MessageLocation.objects.create(message=msg, **loc)

        for r in routes:
            MessageRouteMatch.objects.create(message=msg, **r)

        return msg