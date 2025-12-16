from rest_framework import mixins
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from .models import ParsedMessage, MessageLocation, MessageRouteMatch
from .serializers import ParsedMessageSerializer, MessageLocationSerializer, MessageRouteMatchSerializer
from rest_framework.viewsets import GenericViewSet


class ParsedMessageViewSet(ModelViewSet):
    queryset = ParsedMessage.objects.all().order_by("-created_at")
    serializer_class = ParsedMessageSerializer
    permission_classes = [AllowAny]
    
class MessageLocationViewSet(mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet):
    queryset = MessageLocation.objects.all()
    serializer_class = MessageLocationSerializer
    permission_classes = [AllowAny]
    
class MessageRouteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = MessageRouteMatch.objects.all()
    serializer_class = MessageRouteMatchSerializer
