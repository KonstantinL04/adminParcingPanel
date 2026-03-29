from rest_framework.viewsets import GenericViewSet
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Region, City, Location, RoutePoint, Route, Setting, SettingAPI
from rest_framework import mixins, viewsets
from adminparcing.serializers import ChatSerializer, ExcludedUserSerializer, AlertCategorySerializer, RegionSerializer, CitySerializer, LocationSerializer, RoutePointSerializer, RouteCreateSerializer, RouteSerializer, SettingSerializer, SettingAPISerializer
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from adminparcing.utils.telegram.parsing_controller import parser_controller
from adminparcing.utils.nlp.train_model import train_for_chat, train_all

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

class RegionViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

class CityViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = City.objects.select_related("region").all()
    serializer_class = CitySerializer
    
class LocationViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
 
class RouteViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   GenericViewSet):
    queryset = Route.objects.prefetch_related("points", "points__location")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RouteCreateSerializer
        return RouteSerializer
    
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
    lookup_field = "key"
    lookup_url_kwarg = "key"

class ParserViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["post"])
    def start(self, request):
        ok = parser_controller.start()
        return Response({"status": "started" if ok else "already running"})

    @action(detail=False, methods=["post"])
    def stop(self, request):
        ok = parser_controller.stop()
        return Response({"status": "stopped" if ok else "not running"})

    @action(detail=False, methods=["get"])
    def status(self, request):
        return Response({"running": parser_controller.running})


class NlpViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["post"])
    def train(self, request):
        chat_id = request.data.get("chat_id")
        if chat_id in (None, "", "all"):
            count = train_all()
            return Response({"status": "ok", "trained_chats": count})
        ok = train_for_chat(int(chat_id))
        return Response({"status": "ok" if ok else "no_data", "chat_id": int(chat_id)})
