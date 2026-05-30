from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import timedelta
from django.contrib.gis.measure import D
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .integrations import apply_helper_rating, close_help_map_event, create_help_map_event, make_point
from .models import (
    HelpRequest,
    HelpRequestCandidate,
    HelpRequestChatMessage,
    HelpRequestChatRoom,
    HelpRequestResolution,
    HelpRequestResponse,
    HelperPresence,
)
from .serializers import (
    HelpRequestAcceptSerializer,
    HelpRequestCandidateSerializer,
    HelpRequestChatMessageSerializer,
    HelpRequestChatRoomSerializer,
    HelpRequestCompleteSerializer,
    HelpRequestResolutionSerializer,
    HelpRequestRespondSerializer,
    HelpRequestResponseSerializer,
    HelpRequestSerializer,
    HelperPresenceSerializer,
)


def _publish_help_event(help_request_id, event_type, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        f"help_request_{help_request_id}",
        {
            "type": "help_event",
            "data": {
                "type": event_type,
                "help_request_id": int(help_request_id),
                "payload": payload,
            },
        },
    )


def _publish_help_presence_event(payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "help_presence",
        {
            "type": "help_presence_event",
            "data": {
                "type": "presence_update",
                "payload": payload,
            },
        },
    )


class HelpRequestViewSet(viewsets.ModelViewSet):
    queryset = HelpRequest.objects.select_related("selected_response").prefetch_related("responses").all().order_by("-created_at")
    serializer_class = HelpRequestSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = (self.request.query_params.get("status") or "").strip()
        if status_value:
            statuses = [x.strip() for x in status_value.split(",") if x.strip()]
            qs = qs.filter(status__in=statuses)
        return qs

    def create(self, request, *args, **kwargs):
        creator_user_id = str(request.data.get("creator_user_id") or request.data.get("user_id") or "").strip()
        if not creator_user_id:
            return Response({"detail": "creator_user_id is required"}, status=400)

        location = request.data.get("location") or {}
        coords = location.get("coordinates") if isinstance(location, dict) else None
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return Response({"detail": "location.coordinates is required"}, status=400)
        try:
            point = make_point(coords[0], coords[1])
        except (TypeError, ValueError):
            return Response({"detail": "Invalid coordinates"}, status=400)

        ttl_minutes = int(request.data.get("ttl_minutes") or 120)
        search_radius_m = int(request.data.get("search_radius_m") or 3000)
        description = (request.data.get("description") or request.data.get("details") or "").strip()

        with transaction.atomic():
            event = create_help_map_event(
                location=point,
                description=description,
                creator_user_id=creator_user_id,
                ttl_minutes=ttl_minutes,
            )
            hr = HelpRequest.objects.create(
                event_id=event.get("id"),
                creator_user_id=creator_user_id,
                creator_location=point,
                search_radius_m=search_radius_m,
                description=description,
                status=HelpRequest.STATUS_ACTIVE,
                auto_archive_at=timezone.now() + timedelta(minutes=ttl_minutes),
            )
        data = HelpRequestSerializer(hr, context={"request": request}).data
        _publish_help_event(hr.id, "help_request_created", data)
        return Response(data, status=201)

    @action(detail=True, methods=["get"], url_path="candidates")
    def candidates(self, request, pk=None):
        hr = self.get_object()
        if not hr.creator_location:
            return Response([], status=200)
        nearby = HelperPresence.objects.filter(
            is_available=True,
            last_seen_at__gte=timezone.now() - timedelta(minutes=15),
            location__distance_lte=(hr.creator_location, D(m=hr.search_radius_m)),
        )
        rows = []
        for helper in nearby:
            if helper.user_id == hr.creator_user_id:
                continue
            try:
                distance_m = int(hr.creator_location.distance(helper.location))
            except Exception:
                distance_m = 0
            candidate, _ = HelpRequestCandidate.objects.update_or_create(
                help_request=hr,
                user_id=helper.user_id,
                defaults={"distance_m": distance_m},
            )
            rows.append(candidate)
        return Response(HelpRequestCandidateSerializer(rows, many=True).data)

    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        hr = self.get_object()
        if hr.status not in {HelpRequest.STATUS_ACTIVE, HelpRequest.STATUS_IN_PROGRESS}:
            return Response({"detail": f"Help request is {hr.status}"}, status=400)
        serializer = HelpRequestRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        if user_id == hr.creator_user_id:
            return Response({"detail": "Creator cannot respond to own request"}, status=400)
        resp, created = HelpRequestResponse.objects.get_or_create(
            help_request=hr,
            responder_user_id=user_id,
            defaults={
                "message": serializer.validated_data.get("message", ""),
                "eta_minutes": serializer.validated_data.get("eta_minutes"),
            },
        )
        if not created:
            resp.message = serializer.validated_data.get("message", resp.message)
            if "eta_minutes" in serializer.validated_data:
                resp.eta_minutes = serializer.validated_data.get("eta_minutes")
            resp.save(update_fields=["message", "eta_minutes"])
        if hr.status == HelpRequest.STATUS_ACTIVE:
            hr.status = HelpRequest.STATUS_IN_PROGRESS
            hr.save(update_fields=["status", "updated_at"])
        response_data = HelpRequestResponseSerializer(resp).data
        _publish_help_event(hr.id, "help_request_responded", response_data)
        return Response(response_data, status=201 if created else 200)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        hr = self.get_object()
        serializer = HelpRequestAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = hr.responses.filter(id=serializer.validated_data["response_id"]).first()
        if not response:
            return Response({"detail": "Response not found"}, status=404)
        response.accepted = True
        response.accepted_at = timezone.now()
        response.chat_room_id = response.chat_room_id or f"hr-{hr.id}-{response.responder_user_id}"
        response.save(update_fields=["accepted", "accepted_at", "chat_room_id"])
        room, _ = HelpRequestChatRoom.objects.get_or_create(
            help_request=hr,
            defaults={
                "creator_user_id": hr.creator_user_id,
                "helper_user_id": response.responder_user_id,
                "is_active": True,
            },
        )
        hr.selected_response = response
        hr.status = HelpRequest.STATUS_WAITING_CONFIRMATION
        hr.save(update_fields=["selected_response", "status", "updated_at"])
        payload = {"status": "accepted", "chat_room_id": room.id, "response_id": response.id}
        _publish_help_event(hr.id, "help_request_accepted", payload)
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="chat")
    def chat(self, request, pk=None):
        hr = self.get_object()
        room = getattr(hr, "chat_room", None)
        if not room:
            return Response({"detail": "Chat room not created"}, status=404)
        return Response(HelpRequestChatRoomSerializer(room).data)

    @action(detail=True, methods=["post"], url_path="chat/message")
    def chat_message(self, request, pk=None):
        hr = self.get_object()
        room = getattr(hr, "chat_room", None)
        if not room or not room.is_active:
            return Response({"detail": "Chat room is not active"}, status=400)
        sender_user_id = str(request.data.get("sender_user_id") or "").strip()
        text = (request.data.get("text") or "").strip()
        if sender_user_id not in {room.creator_user_id, room.helper_user_id}:
            return Response({"detail": "Sender is not participant of this chat"}, status=403)
        if not text and not request.FILES.get("attachment"):
            return Response({"detail": "text or attachment is required"}, status=400)
        msg = HelpRequestChatMessage.objects.create(
            room=room,
            sender_user_id=sender_user_id,
            text=text,
            attachment=request.FILES.get("attachment"),
        )
        msg_data = HelpRequestChatMessageSerializer(msg).data
        _publish_help_event(hr.id, "help_chat_message", msg_data)
        return Response(msg_data, status=201)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        hr = self.get_object()
        serializer = HelpRequestCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        helper_user_id = payload.get("helper_user_id") or getattr(getattr(hr, "selected_response", None), "responder_user_id", "")
        if not helper_user_id:
            return Response({"detail": "helper_user_id is required"}, status=400)
        solved = bool(payload["solved"])
        rating_delta = payload.get("rating_delta")
        if rating_delta is None:
            rating_delta = 2 if solved else -2
        resolution, _ = HelpRequestResolution.objects.update_or_create(
            help_request=hr,
            defaults={
                "helper_user_id": helper_user_id,
                "solved": solved,
                "rating_delta": int(rating_delta),
                "rating_comment": payload.get("rating_comment", ""),
                "resolved_by_user_id": payload["resolved_by_user_id"],
            },
        )
        hr.status = HelpRequest.STATUS_COMPLETED if solved else HelpRequest.STATUS_CANCELED
        hr.closed_at = timezone.now()
        hr.save(update_fields=["status", "closed_at", "updated_at"])
        close_help_map_event(hr.event_id)
        room = getattr(hr, "chat_room", None)
        if room and room.is_active:
            room.is_active = False
            room.closed_at = timezone.now()
            room.save(update_fields=["is_active", "closed_at"])
        apply_helper_rating(
            helper_user_id=helper_user_id,
            solved=solved,
            rating_delta=rating_delta,
            rating_comment=payload.get("rating_comment", ""),
            source_object=resolution,
        )
        resolution_data = HelpRequestResolutionSerializer(resolution).data
        _publish_help_event(hr.id, "help_request_completed", resolution_data)
        return Response(resolution_data)


class HelperPresenceViewSet(viewsets.ModelViewSet):
    queryset = HelperPresence.objects.all().order_by("-last_seen_at")
    serializer_class = HelperPresenceSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        user_id = str(request.data.get("user_id") or "").strip()
        lat = request.data.get("lat")
        lon = request.data.get("lon")
        if not user_id or lat is None or lon is None:
            return Response({"detail": "user_id, lat and lon are required"}, status=400)
        try:
            point = make_point(lon, lat)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid coordinates"}, status=400)

        obj, _ = HelperPresence.objects.update_or_create(
            user_id=user_id,
            defaults={
                "location": point,
                "is_available": bool(request.data.get("is_available", True)),
                "reliability_score": float(request.data.get("reliability_score", 0.0) or 0.0),
            },
        )
        data = HelperPresenceSerializer(obj).data
        _publish_help_presence_event(data)
        return Response(data)
