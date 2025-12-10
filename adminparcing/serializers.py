from rest_framework import serializers
from adminparcing.models import Chat, ExcludedUser, EmojiGroup, TextPattern, Location, Setting, SettingAPI
from rest_framework_gis.serializers import GeoFeatureModelSerializer


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"

class ExcludedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludedUser
        fields = "__all__"
        
class EmojiGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmojiGroup
        fields = "__all__"
        
class TextPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextPattern
        fields = "__all__"
        
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