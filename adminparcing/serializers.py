from rest_framework import serializers
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Region, City, Location, Route, RoutePoint, Setting, SettingAPI
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
            "ttl_minutes",
            "confirm_threshold",
            "deny_threshold",
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

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "name")

class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "region", "region_name")
        
class LocationSerializer(GeoFeatureModelSerializer):
    chat_title = serializers.CharField(source="chat.title", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    region_name = serializers.CharField(source="city.region.name", read_only=True)
    region_id = serializers.IntegerField(source="city.region_id", read_only=True)

    class Meta:
        model = Location
        geo_field = "location"
        fields = (
            "id",
            "name",
            "synonyms",
            "chat",
            "chat_title",
            "city",
            "city_name",
            "region_name",
            "region_id",
        )
        
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
    value = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = SettingAPI
        fields = ("id", "key", "value")

    def create(self, validated_data):
        value = validated_data.pop("value", None)
        obj = SettingAPI.objects.create(**validated_data)
        if value is not None:
            obj.value = value
            obj.save(update_fields=["_value"])
        return obj

    def update(self, instance, validated_data):
        value = validated_data.pop("value", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if value is not None:
            instance.value = value
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["value"] = ""
        return data
