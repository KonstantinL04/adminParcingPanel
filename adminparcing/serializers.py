from rest_framework import serializers
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Region, City, Location, Route, RoutePoint, Setting, SettingAPI
from rest_framework_gis.serializers import GeoFeatureModelSerializer
import re
from django.db import IntegrityError, transaction

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
    chats = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Chat.objects.all(),
        required=False
    )
    chat_titles = serializers.SerializerMethodField()
    chat_title = serializers.CharField(source="chat.title", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    region_name = serializers.CharField(source="city.region.name", read_only=True)
    region_id = serializers.IntegerField(source="city.region_id", read_only=True)

    def get_chat_titles(self, obj):
        titles = list(obj.chats.values_list("title", flat=True))
        if titles:
            return titles
        if obj.chat_id:
            return [obj.chat.title]
        return []

    class Meta:
        model = Location
        geo_field = "location"
        fields = (
            "id",
            "name",
            "synonyms",
            "chat",
            "chats",
            "chat_title",
            "chat_titles",
            "city",
            "city_name",
            "region_name",
            "region_id",
        )

    def create(self, validated_data):
        chats = validated_data.pop("chats", [])
        location = super().create(validated_data)
        if chats:
            location.chats.set(chats)
            if not location.chat_id:
                location.chat = chats[0]
                location.save(update_fields=["chat"])
        return location

    def update(self, instance, validated_data):
        chats = validated_data.pop("chats", None)
        location = super().update(instance, validated_data)
        if chats is not None:
            location.chats.set(chats)
            if not location.chat_id and chats:
                location.chat = chats[0]
                location.save(update_fields=["chat"])
        return location
        
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
    chats = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    chat_titles = serializers.SerializerMethodField()

    start_point_name = serializers.CharField(
        source="start_point.name",
        read_only=True
    )
    end_point_name = serializers.CharField(
        source="end_point.name",
        read_only=True
    )

    def get_chat_titles(self, obj):
        return list(obj.chats.values_list("title", flat=True))

    class Meta:
        model = Route
        fields = (
            "id",
            "name",
            "chats",
            "chat_titles",
            "start_point",
            "start_point_name",
            "end_point",
            "end_point_name",
            "enabled",
            "points",
        )

class RouteCreateSerializer(serializers.ModelSerializer):
    chats = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Chat.objects.all(),
        required=True,
        allow_empty=False
    )
    points = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = Route
        fields = [
            "id",
            "name",
            "chats",
            "start_point",
            "end_point",
            "enabled",
            "points",
        ]

    @staticmethod
    def _location_matches_chats(location, chat_ids):
        if not chat_ids:
            return True
        loc_chat_ids = set(location.chats.values_list("id", flat=True))
        if location.chat_id:
            loc_chat_ids.add(location.chat_id)
        return bool(loc_chat_ids.intersection(chat_ids))

    def validate(self, attrs):
        chats = attrs.get("chats", None)
        chat_ids = set(c.id for c in chats) if chats is not None else set()

        start_point = attrs.get("start_point")
        end_point = attrs.get("end_point")
        point_ids = attrs.get("points", [])

        if chats is not None and len(chat_ids) == 0:
            raise serializers.ValidationError({"chats": "Выберите хотя бы один чат."})

        if start_point and not self._location_matches_chats(start_point, chat_ids):
            raise serializers.ValidationError({"start_point": "Начальная точка не относится к выбранным чатам."})

        if end_point and not self._location_matches_chats(end_point, chat_ids):
            raise serializers.ValidationError({"end_point": "Конечная точка не относится к выбранным чатам."})

        if start_point and end_point and start_point.id == end_point.id:
            raise serializers.ValidationError({"end_point": "Начальная и конечная точки должны отличаться."})

        if point_ids and chat_ids:
            bad_points = []
            for location_id in point_ids:
                try:
                    loc = Location.objects.prefetch_related("chats").get(id=location_id)
                except Location.DoesNotExist:
                    bad_points.append(location_id)
                    continue
                if not self._location_matches_chats(loc, chat_ids):
                    bad_points.append(location_id)
            if bad_points:
                raise serializers.ValidationError({"points": "Некоторые точки не относятся к выбранным чатам."})

        return attrs

    def create(self, validated_data):
        chats = validated_data.pop("chats", [])
        points = validated_data.pop("points", [])
        try:
            with transaction.atomic():
                route = Route.objects.create(**validated_data)
                if chats:
                    route.chats.set(chats)

                for idx, location_id in enumerate(points):
                    RoutePoint.objects.create(
                        route=route,
                        location_id=location_id,
                        order=idx
                    )
                return route
        except IntegrityError:
            raise serializers.ValidationError({
                "detail": "Не удалось сохранить маршрут. Проверьте уникальность названия и выбранные точки."
            })

    def update(self, instance, validated_data):
        chats = validated_data.pop("chats", None)
        points = validated_data.pop("points", None)

        try:
            with transaction.atomic():
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()

                if chats is not None:
                    instance.chats.set(chats)

                if points is not None:
                    instance.points.all().delete()
                    for idx, location_id in enumerate(points):
                        RoutePoint.objects.create(
                            route=instance,
                            location_id=location_id,
                            order=idx
                        )
        except IntegrityError:
            raise serializers.ValidationError({
                "detail": "Не удалось обновить маршрут. Проверьте уникальность названия и выбранные точки."
            })
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
