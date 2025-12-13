from rest_framework.viewsets import GenericViewSet
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Location, Setting, SettingAPI
from rest_framework import mixins, viewsets
from adminparcing.serializers import ChatSerializer, ExcludedUserSerializer, AlertCategorySerializer, LocationSerializer, SettingSerializer, SettingAPISerializer
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from adminparcing.utils.telegram.parsing_controller import parser_controller

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
    
class AlertCategoryViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = AlertCategory.objects.all()
    serializer_class = AlertCategorySerializer
    
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


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def start_parser(request):
    ok = parser_controller.start()
    return Response({"status": "started" if ok else "already running"})


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def stop_parser(request):
    ok = parser_controller.stop()
    return Response({"status": "stopped" if ok else "not running"})


@api_view(["GET"])
@ensure_csrf_cookie
def parser_status(request):
    return Response({"running": parser_controller.running})
