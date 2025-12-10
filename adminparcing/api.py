from rest_framework.viewsets import GenericViewSet
from adminparcing.models import Chat, ExcludedUser, EmojiGroup, TextPattern, Location, Setting, SettingAPI
from rest_framework import mixins, viewsets
from adminparcing.serializers import ChatSerializer, ExcludedUserSerializer, EmojiGroupSerializer, TextPatternSerializer, LocationSerializer, SettingSerializer, SettingAPISerializer

class ChatViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    
class ExcludedUserViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = ExcludedUser.objects.all()
    serializer_class = ExcludedUserSerializer
    
class EmojiGroupViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = EmojiGroup.objects.all()
    serializer_class = EmojiGroupSerializer
    
class TextPatternViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = TextPattern.objects.all()
    serializer_class = TextPatternSerializer
    
class LocationViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    
class SettingViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    
class SettingAPIViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = SettingAPI.objects.all()
    serializer_class = SettingAPISerializer