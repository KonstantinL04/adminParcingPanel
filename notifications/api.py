import math

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .integrations import get_events_in_bbox
from .models import NotificationTemplate, DeviceToken, NotificationJob, NotificationDelivery
from .permissions import IsStaffOrSuperuser
from .serializers import (
    NotificationTemplateSerializer,
    DeviceTokenSerializer,
    NotificationJobSerializer,
    NotificationDeliverySerializer,
    NotificationSendSerializer,
)


def _angular_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def _bearing_degrees(lat1, lon1, lat2, lon2):
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    y = math.sin(delta_lon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _distance_meters(lat1, lon1, lat2, lon2):
    earth_radius_m = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _destination_point(lat, lon, bearing, distance_m):
    earth_radius_m = 6371000
    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    angular_distance = distance_m / earth_radius_m

    result_lat = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )
    result_lon = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(result_lat),
    )
    return math.degrees(result_lat), ((math.degrees(result_lon) + 540) % 360) - 180


def _relative_offsets_m(lat1, lon1, lat2, lon2, heading):
    mean_lat = math.radians((lat1 + lat2) / 2)
    east_m = (lon2 - lon1) * 111_320 * math.cos(mean_lat)
    north_m = (lat2 - lat1) * 111_320
    heading_rad = math.radians(heading)
    heading_east = math.sin(heading_rad)
    heading_north = math.cos(heading_rad)
    ahead_m = east_m * heading_east + north_m * heading_north
    lateral_m = east_m * heading_north - north_m * heading_east
    return ahead_m, lateral_m


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _event_zone_directions(event):
    direction = event.get("direction")
    try:
        direction = float(direction) % 360
    except (TypeError, ValueError):
        return []

    directions = [direction]
    try:
        dir_type = int(event.get("dir_type") or 1)
    except (TypeError, ValueError):
        dir_type = 1
    if dir_type == 2:
        directions.append((direction + 180) % 360)
    return directions


def _event_action_zone(event, event_lat, event_lon):
    try:
        distance_m = float(event.get("distance") or 0)
        angle_deg = float(event.get("angle") or 0)
    except (TypeError, ValueError):
        return None

    directions = _event_zone_directions(event)
    if not directions or distance_m <= 0 or angle_deg <= 0:
        return None

    distance_m = max(10, min(distance_m, 3000))
    angle_deg = max(5, min(angle_deg, 180))
    half_angle = angle_deg / 2
    step_count = max(6, min(24, int(angle_deg / 8)))
    polygons = []

    for direction in directions:
        coordinates = [[event_lon, event_lat]]
        for idx in range(step_count + 1):
            bearing = direction - half_angle + angle_deg * (idx / step_count)
            lat, lon = _destination_point(event_lat, event_lon, bearing, distance_m)
            coordinates.append([round(lon, 7), round(lat, 7)])
        coordinates.append([event_lon, event_lat])
        polygons.append({
            "direction": round(direction, 1),
            "coordinates": coordinates,
        })

    return {
        "type": "sector",
        "dir_type": event.get("dir_type") or 1,
        "direction": event.get("direction") or 0,
        "distance_m": int(distance_m),
        "angle_deg": int(angle_deg),
        "polygons": polygons,
        "geojson": {
            "type": "MultiPolygon",
            "coordinates": [[polygon["coordinates"]] for polygon in polygons],
        },
    }


def _is_inside_event_zone(event, user_lat, user_lon, event_lat, event_lon):
    zone = _event_action_zone(event, event_lat, event_lon)
    if not zone:
        return False

    distance_m = _distance_meters(event_lat, event_lon, user_lat, user_lon)
    if distance_m > zone["distance_m"] + 25:
        return False

    bearing = _bearing_degrees(event_lat, event_lon, user_lat, user_lon)
    half_angle = zone["angle_deg"] / 2
    return any(_angular_diff(direction, bearing) <= half_angle + 5 for direction in _event_zone_directions(event))


def _event_alert_text(event, distance_m):
    distance = int(round(distance_m / 10) * 10)
    if distance < 100:
        distance_text = "Рядом"
    else:
        distance_text = f"Через {distance} метров"

    class_name = (event.get("class_name") or event.get("category_class_name") or "дорожное событие")
    category_name = event.get("category_name") or ""

    parts = [distance_text, class_name.lower()]
    if event.get("speed_limit"):
        parts.append(f"на {event['speed_limit']}")
    if category_name:
        parts.append(category_name.lower())
    return ", ".join(parts)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all().order_by("code")
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsStaffOrSuperuser]


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all().order_by("-last_seen_at")
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return qs
        return qs.filter(user_id=user.id)

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        token = str(request.data.get("token") or "").strip()
        platform = str(request.data.get("platform") or "").strip()
        user_id = int(request.data.get("user_id") or request.user.id or 0)
        if not token or not platform:
            return Response({"detail": "token and platform are required"}, status=400)
        if not (request.user.is_staff or request.user.is_superuser) and user_id != request.user.id:
            return Response({"detail": "Cannot register token for another user"}, status=403)

        obj, _ = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user_id": user_id,
                "platform": platform,
                "enabled": bool(request.data.get("enabled", True)),
            },
        )
        return Response(DeviceTokenSerializer(obj).data)


class NotificationJobViewSet(viewsets.ModelViewSet):
    queryset = NotificationJob.objects.select_related("template").prefetch_related("deliveries").all().order_by("-created_at")
    serializer_class = NotificationJobSerializer
    permission_classes = [IsStaffOrSuperuser]

    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        serializer = NotificationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        template = None
        title = payload.get("title", "")
        body = payload.get("body", "")
        if payload.get("template_code"):
            template = NotificationTemplate.objects.filter(code=payload["template_code"], enabled=True).first()
            if not template:
                return Response({"detail": "Template not found or disabled"}, status=404)
            title = template.title_template
            body = template.body_template

        with transaction.atomic():
            job = NotificationJob.objects.create(
                source_service=payload.get("source_service", ""),
                template=template,
                title=title,
                body=body,
                payload=payload.get("payload", {}),
                recipients=payload["recipients"],
                scheduled_at=payload.get("scheduled_at"),
                created_by_user_id=str(request.user.id),
            )
            self._create_pending_deliveries(job)

        data = NotificationJobSerializer(job, context={"request": request}).data
        return Response(data, status=201)

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch(self, request, pk=None):
        job = self.get_object()
        if job.status in (NotificationJob.STATUS_COMPLETED, NotificationJob.STATUS_FAILED):
            return Response({"detail": f"Job already {job.status}"}, status=400)
        if job.scheduled_at and timezone.now() < job.scheduled_at:
            return Response({"detail": "Job is scheduled for future"}, status=400)

        job.status = NotificationJob.STATUS_PROCESSING
        job.started_at = job.started_at or timezone.now()
        job.save(update_fields=["status", "started_at", "updated_at"])

        pending = job.deliveries.filter(status=NotificationDelivery.STATUS_PENDING)
        for delivery in pending:
            delivery.attempts += 1
            if not delivery.token:
                delivery.status = NotificationDelivery.STATUS_FAILED
                delivery.error_text = "No active device token"
                delivery.save(update_fields=["attempts", "status", "error_text", "updated_at"])
                continue

            # Mock provider delivery path. Here we emulate successful push dispatch.
            delivery.provider = "mock"
            delivery.provider_message_id = f"mock-{job.id}-{delivery.id}"
            delivery.status = NotificationDelivery.STATUS_SENT
            delivery.sent_at = timezone.now()
            delivery.error_text = ""
            delivery.save(
                update_fields=[
                    "attempts",
                    "provider",
                    "provider_message_id",
                    "status",
                    "sent_at",
                    "error_text",
                    "updated_at",
                ]
            )

        total = job.deliveries.count()
        success = job.deliveries.filter(status=NotificationDelivery.STATUS_SENT).count()
        failed = job.deliveries.filter(status=NotificationDelivery.STATUS_FAILED).count()
        job.total = total
        job.success = success
        job.failed = failed
        job.status = NotificationJob.STATUS_COMPLETED if failed == 0 else NotificationJob.STATUS_FAILED
        job.finished_at = timezone.now()
        job.save(update_fields=["total", "success", "failed", "status", "finished_at", "updated_at"])
        return Response(NotificationJobSerializer(job, context={"request": request}).data)

    def _create_pending_deliveries(self, job: NotificationJob):
        recipients = [int(x) for x in (job.recipients or []) if isinstance(x, int) or str(x).isdigit()]
        tokens = list(
            DeviceToken.objects.filter(user_id__in=recipients, enabled=True).order_by("-last_seen_at")
        )
        newest_token_by_user = {}
        for token in tokens:
            newest_token_by_user.setdefault(token.user_id, token)

        delivery_rows = []
        for user_id in recipients:
            token_obj = newest_token_by_user.get(user_id)
            delivery_rows.append(
                NotificationDelivery(
                    job=job,
                    device=token_obj,
                    user_id=user_id,
                    token=token_obj.token if token_obj else "",
                    channel=NotificationDelivery.CHANNEL_PUSH,
                    status=NotificationDelivery.STATUS_PENDING,
                )
            )
        NotificationDelivery.objects.bulk_create(delivery_rows)
        job.total = len(delivery_rows)
        job.save(update_fields=["total", "updated_at"])


class NotificationDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationDelivery.objects.select_related("job", "device").all().order_by("-created_at")
    serializer_class = NotificationDeliverySerializer
    permission_classes = [IsStaffOrSuperuser]

    def get_queryset(self):
        qs = super().get_queryset()
        job_id = self.request.query_params.get("job")
        status_value = (self.request.query_params.get("status") or "").strip()
        if job_id and str(job_id).isdigit():
            qs = qs.filter(job_id=int(job_id))
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class DrivingAlertViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="check")
    def check(self, request):
        try:
            lat = float(request.data.get("lat"))
            lon = float(request.data.get("lon"))
        except (TypeError, ValueError):
            return Response({"detail": "lat and lon are required"}, status=400)

        radius_m = _safe_int(request.data.get("radius_m"), 500)
        radius_m = max(50, min(radius_m, 1500))
        front_angle = _safe_int(request.data.get("front_angle"), 40)
        front_angle = max(10, min(front_angle, 90))
        corridor_width_m = _safe_int(request.data.get("corridor_width_m"), 90)
        corridor_width_m = max(20, min(corridor_width_m, 300))
        corridor_half_width_m = corridor_width_m / 2
        limit = _safe_int(request.data.get("limit"), 5)
        limit = max(1, min(limit, 20))

        heading = _safe_float(request.data.get("heading"))
        if heading is None:
            heading = _safe_float(request.data.get("course"))
        if heading is None:
            heading = _safe_float(request.data.get("bearing"))
        if heading is None:
            return Response({"detail": "heading is required for driving alerts"}, status=400)
        heading = heading % 360

        speed_kmh = _safe_float(request.data.get("speed_kmh"), 0) or 0

        delta_lat = radius_m / 111_320
        delta_lon = radius_m / max(1, 111_320 * math.cos(math.radians(lat)))
        try:
            qs = get_events_in_bbox(
                min_lon=lon - delta_lon,
                min_lat=lat - delta_lat,
                max_lon=lon + delta_lon,
                max_lat=lat + delta_lat,
                limit=500,
            )
        except Exception as exc:
            return Response({"detail": f"events request failed: {exc}"}, status=502)

        alerts = []
        for event in qs:
            coordinates = (event.get("location") or {}).get("coordinates") or []
            if len(coordinates) < 2:
                continue
            event_lon = float(coordinates[0])
            event_lat = float(coordinates[1])
            distance_m = _distance_meters(lat, lon, event_lat, event_lon)
            if distance_m > radius_m:
                continue

            bearing = _bearing_degrees(lat, lon, event_lat, event_lon)
            angle_diff = _angular_diff(heading, bearing)
            ahead_m, lateral_m = _relative_offsets_m(lat, lon, event_lat, event_lon, heading)

            if ahead_m <= 0 or ahead_m > radius_m:
                continue
            if angle_diff > front_angle:
                continue
            if abs(lateral_m) > corridor_half_width_m:
                continue

            action_zone = _event_action_zone(event, event_lat, event_lon)
            inside_action_zone = _is_inside_event_zone(event, lat, lon, event_lat, event_lon)
            alerts.append({
                "event_id": event.get("id"),
                "class_item": event.get("class_item"),
                "category_name": event.get("category_name") or "",
                "class_name": event.get("class_name") or "",
                "category_icon": event.get("category_icon") or "",
                "details": event.get("details") or "",
                "source_kind": event.get("source_kind") or "",
                "status": event.get("status") or "",
                "speed_limit": event.get("speed_limit") or 0,
                "dir_type": event.get("dir_type") or 1,
                "direction": event.get("direction") or 0,
                "zone_distance_m": event.get("distance") or 0,
                "zone_angle_deg": event.get("angle") or 0,
                "distance_m": int(ahead_m),
                "radial_distance_m": int(distance_m),
                "distance_ahead_m": int(ahead_m),
                "lateral_offset_m": int(abs(lateral_m)),
                "bearing": round(bearing, 1),
                "angle_diff": round(angle_diff, 1),
                "inside_action_zone": inside_action_zone,
                "location": {
                    "type": "Point",
                    "coordinates": [event_lon, event_lat],
                },
                "action_zone": action_zone,
                "alert_text": _event_alert_text(event, ahead_m),
            })

        alerts.sort(key=lambda item: item["distance_ahead_m"])
        alerts = alerts[:limit]
        return Response({
            "alerts": alerts,
            "count": len(alerts),
            "voice_text": alerts[0]["alert_text"] if alerts else "",
            "speech": {
                "text": alerts[0]["alert_text"] if alerts else "",
                "language": "ru-RU",
                "engine": "iOS Speech Synthesizer",
            },
            "filter": {
                "radius_m": radius_m,
                "heading": round(heading, 1),
                "front_angle": front_angle,
                "corridor_width_m": corridor_width_m,
                "corridor_half_width_m": int(corridor_half_width_m),
            },
        })
