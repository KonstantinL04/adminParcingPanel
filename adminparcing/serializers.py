from rest_framework import serializers
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Location, Setting, SettingAPI
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
        
class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = "__all__"
        
class SettingAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingAPI
        fields = "__all__"