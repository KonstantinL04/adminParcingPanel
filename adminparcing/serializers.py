from rest_framework import serializers
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Location, Route, RoutePoint, Setting, SettingAPI
from rest_framework_gis.serializers import GeoFeatureModelSerializer
import re

class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"

class ExcludedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludedUser
        fields = "__all__"
        
class AlertCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertCategory
        fields = [
            "id",
            "name",
            "text_patterns",
            "emoji_patterns",
            "enabled",
        ]

    def validate_text_patterns(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("text_patterns должен быть массивом")
        for p in value:
            if not isinstance(p, str):
                raise serializers.ValidationError("Все паттерны должны быть строками")
        return value

    def validate_emoji_patterns(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("emoji_patterns должен быть массивом")
        for e in value:
            if not isinstance(e, str):
                raise serializers.ValidationError("Все эмодзи должны быть строками")
        return value
        
class LocationSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Location
        geo_field = "location"
        fields = ("id", "name", "synonyms")
        
class RoutePointSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(
        source="location.name",
        read_only=True
    )

    class Meta:
        model = RoutePoint
        fields = (
            "id",
            "order",
            "location",
            "location_name",
        )
        
class RouteSerializer(serializers.ModelSerializer):
    points = RoutePointSerializer(many=True, read_only=True)

    start_point_name = serializers.CharField(
        source="start_point.name",
        read_only=True
    )
    end_point_name = serializers.CharField(
        source="end_point.name",
        read_only=True
    )

    class Meta:
        model = Route
        fields = (
            "id",
            "name",
            "start_point",
            "start_point_name",
            "end_point",
            "end_point_name",
            "enabled",
            "points",
        )

class RouteCreateSerializer(serializers.ModelSerializer):
    points = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = Route
        fields = [
            "id",
            "name",
            "start_point",
            "end_point",
            "enabled",
            "points",
        ]

    def create(self, validated_data):
        points = validated_data.pop("points", [])
        route = Route.objects.create(**validated_data)

        for idx, location_id in enumerate(points):
            RoutePoint.objects.create(
                route=route,
                location_id=location_id,
                order=idx
            )
        return route

    def update(self, instance, validated_data):
        points = validated_data.pop("points", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if points is not None:
            instance.points.all().delete()
            for idx, location_id in enumerate(points):
                RoutePoint.objects.create(
                    route=instance,
                    location_id=location_id,
                    order=idx
                )
        return instance

class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = "__all__"
        
class SettingAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingAPI
        fields = "__all__"