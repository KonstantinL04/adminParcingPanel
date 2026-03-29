from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from .models import ParsedMessage, RoadEvent, EventVote
from .serializers import (
    ParsedMessageSerializer,
    RoadEventSerializer,
    RoadEventCreateSerializer,
    EventVoteSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from adminparcing.services.aggregator import process_parsed_message
from adminparcing.services.event_status import get_ttl_minutes, recalc_event_from_votes
class ParsedMessageViewSet(ModelViewSet):
    queryset = ParsedMessage.objects.select_related("chat", "category").all()
    serializer_class = ParsedMessageSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        parsed_message = serializer.save()
        
        process_parsed_message(parsed_message, self.request.data.get("locations", []))
    

class RoadEventViewSet(ModelViewSet):
    queryset = RoadEvent.objects.filter(status__in=["active", "confirmed"]).order_by("-last_activity_at")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return RoadEventCreateSerializer
        return RoadEventSerializer
    

class EventVoteViewSet(ModelViewSet):
    queryset = EventVote.objects.all()
    serializer_class = EventVoteSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        event_id = request.data.get("event")
        vote = int(request.data.get("vote"))
        lat = request.data.get("lat")
        lon = request.data.get("lon")

        voter_point = Point(lon, lat, srid=4326)
        event = RoadEvent.objects.get(id=event_id)

        # Проверка радиуса 500 м
        if event.location.distance(voter_point) > 500:
            return Response(
                {"detail": "Too far from event"},
                status=403
            )

        obj, created = EventVote.objects.update_or_create(
            event=event,
            user_id=request.data.get("user_id"),
            defaults={
                "vote": vote,
                "voter_location": voter_point,
            }
        )

        # Обновляем агрегаты и продлеваем актуальность
        event.last_activity_at = obj.created_at
        event.save(update_fields=["last_activity_at"])
        recalc_event_from_votes(event)

        return Response(EventVoteSerializer(obj).data)
