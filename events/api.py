# api.py

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.gis.measure import D
from django.db import models as django_models
from django.db import transaction
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import io, csv
from pathlib import Path
from django.http import HttpResponse
from .models import (
    EventClass,
    EventClassItem,
    MapEvent,
    EventMedia,
    EntityVote,
    PocketGisSource,
    PocketGisImport,
)
from .serializers import (
    EventClassSerializer,
    EventClassItemSerializer,
    EventClassCatalogSerializer,
    EventMediaSerializer,
    EventMediaUploadSerializer,
    MapEventListSerializer,
    MapEventDetailSerializer,
    MapEventUpdateSerializer,
    MapEventCreateSerializer,
    EntityVoteSerializer,
    PocketGisSourceSerializer,
    PocketGisImportSerializer,
)

def _weather_condition_from_code(code):
    try:
        value = int(code)
    except (TypeError, ValueError):
        return "Неизвестно", "Clear"
    if value == 0:
        return "ясно", "Clear"
    if value in (1, 2, 3):
        return "переменная облачность", "Clouds"
    if value in (45, 48):
        return "туман", "Mist"
    if value in (51, 53, 55, 56, 57):
        return "морось", "Drizzle"
    if value in (61, 63, 65, 66, 67, 80, 81, 82):
        return "дождь", "Rain"
    if value in (71, 73, 75, 77, 85, 86):
        return "снег", "Snow"
    if value in (95, 96, 99):
        return "гроза", "Thunderstorm"
    return "облачно", "Clouds"


def _round_weather_value(value):
    if value is None:
        return None
    return round(float(value))


def _build_open_meteo_hourly(payload):
    current_time = str((payload.get("current") or {}).get("time") or "")
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temperatures = hourly.get("temperature_2m") or []
    feels_like = hourly.get("apparent_temperature") or []
    weather_codes = hourly.get("weather_code") or []
    wind_speeds = hourly.get("wind_speed_10m") or []
    precipitation = hourly.get("precipitation_probability") or []

    start_index = 0
    if current_time:
        for idx, time_value in enumerate(times):
            if str(time_value) >= current_time:
                start_index = idx
                break

    rows = []
    for idx in range(start_index, min(start_index + 24, len(times))):
        time_value = times[idx]
        condition, condition_code = _weather_condition_from_code(
            weather_codes[idx] if idx < len(weather_codes) else None
        )
        rows.append({
            "time": time_value,
            "temperature": _round_weather_value(temperatures[idx] if idx < len(temperatures) else None),
            "feels_like": _round_weather_value(feels_like[idx] if idx < len(feels_like) else None),
            "condition": condition,
            "condition_code": condition_code,
            "wind_speed": wind_speeds[idx] if idx < len(wind_speeds) else None,
            "precipitation_probability": precipitation[idx] if idx < len(precipitation) else None,
        })
    return rows


def _build_open_meteo_daily(payload):
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    temp_max = daily.get("temperature_2m_max") or []
    temp_min = daily.get("temperature_2m_min") or []
    weather_codes = daily.get("weather_code") or []
    precipitation = daily.get("precipitation_probability_max") or []
    wind_speeds = daily.get("wind_speed_10m_max") or []

    rows = []
    for idx, time_value in enumerate(times[:7]):
        condition, condition_code = _weather_condition_from_code(
            weather_codes[idx] if idx < len(weather_codes) else None
        )
        rows.append({
            "date": time_value,
            "temperature_max": _round_weather_value(temp_max[idx] if idx < len(temp_max) else None),
            "temperature_min": _round_weather_value(temp_min[idx] if idx < len(temp_min) else None),
            "condition": condition,
            "condition_code": condition_code,
            "precipitation_probability": precipitation[idx] if idx < len(precipitation) else None,
            "wind_speed": wind_speeds[idx] if idx < len(wind_speeds) else None,
        })
    return rows


def _fetch_open_meteo_weather(lat_value, lon_value):
    query = urllib.parse.urlencode({
        "latitude": lat_value,
        "longitude": lon_value,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
            "precipitation_probability",
        ]),
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ]),
        "wind_speed_unit": "ms",
        "forecast_days": 7,
        "timezone": "auto",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{query}"
    with urllib.request.urlopen(url, timeout=7) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current") or {}
    condition, condition_code = _weather_condition_from_code(current.get("weather_code"))
    return {
        "location": "",
        "country": "",
        "temperature": _round_weather_value(current.get("temperature_2m")),
        "feels_like": _round_weather_value(current.get("apparent_temperature")),
        "humidity": current.get("relative_humidity_2m"),
        "pressure": None,
        "wind_speed": current.get("wind_speed_10m"),
        "wind_deg": current.get("wind_direction_10m"),
        "clouds": current.get("cloud_cover"),
        "condition": condition,
        "condition_code": condition_code,
        "icon": "",
        "coordinates": {
            "lat": lat_value,
            "lon": lon_value,
        },
        "hourly": _build_open_meteo_hourly(payload),
        "daily": _build_open_meteo_daily(payload),
        "source": "Open-Meteo",
    }


class WeatherViewSet(viewsets.GenericViewSet):
    """Погодный контекст по координатам пользователя."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        if lat is None or lon is None:
            return Response({"detail": "lat and lon are required"}, status=400)

        try:
            lat_value = float(lat)
            lon_value = float(lon)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid coordinates"}, status=400)

        api_key = getattr(settings, "OPENWEATHER_API_KEY", "")
        if not api_key:
            return Response(_fetch_open_meteo_weather(lat_value, lon_value))

        query = urllib.parse.urlencode({
            "lat": lat_value,
            "lon": lon_value,
            "appid": api_key,
            "units": "metric",
            "lang": "ru",
        })
        url = f"https://api.openweathermap.org/data/2.5/weather?{query}"

        openweather_error = None
        try:
            with urllib.request.urlopen(url, timeout=7) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            openweather_error = str(exc)
            try:
                return Response(_fetch_open_meteo_weather(lat_value, lon_value))
            except Exception as fallback_exc:
                return Response({
                    "detail": f"weather request failed: {openweather_error}; fallback failed: {fallback_exc}"
                }, status=502)

        weather = (payload.get("weather") or [{}])[0]
        main = payload.get("main") or {}
        wind = payload.get("wind") or {}
        clouds = payload.get("clouds") or {}
        sys = payload.get("sys") or {}
        hourly = []
        daily = []
        try:
            forecast = _fetch_open_meteo_weather(lat_value, lon_value)
            hourly = forecast.get("hourly", [])
            daily = forecast.get("daily", [])
        except Exception:
            hourly = []
            daily = []

        return Response({
            "location": payload.get("name") or "",
            "country": sys.get("country") or "",
            "temperature": round(float(main.get("temp", 0))),
            "feels_like": round(float(main.get("feels_like", 0))),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"),
            "wind_deg": wind.get("deg"),
            "clouds": clouds.get("all"),
            "condition": weather.get("description") or "",
            "condition_code": weather.get("main") or "",
            "icon": weather.get("icon") or "",
            "coordinates": {
                "lat": lat_value,
                "lon": lon_value,
            },
            "hourly": hourly,
            "daily": daily,
            "source": "OpenWeather",
        })


class MapSearchViewSet(viewsets.GenericViewSet):
    """Поиск мест для карты."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        query_text = (request.query_params.get("q") or "").strip()
        if not query_text:
            return Response({"detail": "q is required"}, status=400)

        query = urllib.parse.urlencode({
            "format": "jsonv2",
            "q": query_text,
            "limit": 6,
            "accept-language": "ru",
            "addressdetails": 1,
        })
        url = f"https://nominatim.openstreetmap.org/search?{query}"
        request_obj = urllib.request.Request(
            url,
            headers={"User-Agent": "RoadHelperAdminPanel/1.0"},
        )

        try:
            with urllib.request.urlopen(request_obj, timeout=7) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return Response({"detail": f"map search failed: {exc}"}, status=502)

        results = []
        for item in payload:
            try:
                lat = float(item.get("lat"))
                lon = float(item.get("lon"))
            except (TypeError, ValueError):
                continue
            title = item.get("name") or item.get("display_name") or query_text
            results.append({
                "title": title,
                "subtitle": item.get("display_name") or "",
                "coords": [lat, lon],
            })

        return Response({"results": results})


class EventClassViewSet(viewsets.ModelViewSet):
    """Классы событий"""
    queryset = EventClass.objects.all().order_by("sort_order", "name")
    serializer_class = EventClassSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        """Каталог: классы + элементы"""
        classes = EventClass.objects.filter(enabled=True).prefetch_related("items").order_by("sort_order", "name")
        serializer = EventClassCatalogSerializer(classes, many=True, context={"request": request})
        return Response(serializer.data)


class EventClassItemViewSet(viewsets.ModelViewSet):
    """Элементы классов (категории)"""
    serializer_class = EventClassItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = EventClassItem.objects.select_related("event_class").order_by(
            "event_class__sort_order", "sort_order", "name"
        )
        source_kind = self.request.query_params.get("source_kind")
        if source_kind:
            qs = qs.filter(source_kind=source_kind)
        enabled = self.request.query_params.get("enabled")
        if enabled is not None:
            qs = qs.filter(enabled=str(enabled).lower() in {"1", "true", "yes"})
        return qs


class MapEventViewSet(viewsets.ModelViewSet):
    """Точки на карте"""
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return MapEventListSerializer
        if self.action == "retrieve":
            return MapEventDetailSerializer
        if self.action in ("update", "partial_update"):
            return MapEventUpdateSerializer
        if self.action == "create":
            return MapEventCreateSerializer
        return MapEventListSerializer

    def get_queryset(self):
        qs = MapEvent.objects.filter(is_active=True).select_related("class_item__event_class").prefetch_related("media")

        region = self.request.query_params.get("region")
        category = self.request.query_params.get("category")
        search = (self.request.query_params.get("search") or "").strip()
        bbox = (self.request.query_params.get("bbox") or "").strip()
        source_kind = self.request.query_params.get("source_kind")
        source = self.request.query_params.get("source")

        if source_kind:
            qs = qs.filter(source_kind=source_kind)
        if source:
            qs = qs.filter(source_id=source)
        if region:
            qs = qs.filter(region_id=region)
        if category:
            qs = qs.filter(class_item_id=category)
        if search:
            qs = qs.filter(details__icontains=search)
        if bbox:
            parts = [p.strip() for p in bbox.split(",")]
            if len(parts) == 4:
                min_lon, min_lat, max_lon, max_lat = map(float, parts)
                bbox_polygon = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
                bbox_polygon.srid = 4326
                qs = qs.filter(location__within=bbox_polygon)

        return qs.order_by("-last_seen_at", "id")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        limit = min(max(int(request.query_params.get("limit", 500)), 1), 5000)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        count = qs.count()
        items = qs[offset:offset + limit]
        serializer = self.get_serializer(items, many=True)
        return Response({
            "limit": limit,
            "offset": offset,
            "count": count,
            "results": serializer.data,
        })

    @action(detail=False, methods=["post"], url_path="from-parsed")
    def from_parsed(self, request):
        """Прием результата парсинга из сервиса Telegram-чатов."""
        try:
            lon = float(request.data.get("lon"))
            lat = float(request.data.get("lat"))
        except (TypeError, ValueError):
            return Response({"detail": "lon and lat are required"}, status=400)

        category_id = request.data.get("category_id")
        class_item = None
        if category_id:
            class_item = EventClassItem.objects.filter(id=category_id, enabled=True).first()
            if not class_item:
                return Response({"detail": "Category not found"}, status=404)

        parsed_message_id = request.data.get("parsed_message_id")
        telegram_message_id = request.data.get("telegram_message_id")
        point = Point(lon, lat, srid=4326)
        radius_m = int(request.data.get("dedup_radius_m") or 50)
        created_at = parse_datetime(str(request.data.get("created_at") or "")) or timezone.now()

        event = (
            MapEvent.objects
            .filter(
                source_kind=MapEvent.SOURCE_DYNAMIC,
                source="telegram",
                class_item=class_item,
                status__in=[MapEvent.STATUS_ACTIVE, MapEvent.STATUS_CONFIRMED],
                location__distance_lte=(point, D(m=radius_m)),
            )
            .order_by("-last_seen_at")
            .first()
        )

        if event:
            if created_at and created_at <= event.last_seen_at:
                return Response(MapEventDetailSerializer(event, context={"request": request}).data)
            event.confirmations += 1
            event.confidence = min(1.0, event.confidence + 0.1)
            event.save(update_fields=["confirmations", "confidence", "last_seen_at"])
            return Response(MapEventDetailSerializer(event, context={"request": request}).data)

        ttl_minutes = getattr(class_item, "ttl_minutes", 60) if class_item else 60
        event = MapEvent.objects.create(
            source_kind=MapEvent.SOURCE_DYNAMIC,
            source="telegram",
            source_name=request.data.get("chat_title") or "",
            source_object_id=f"telegram:{telegram_message_id or parsed_message_id or ''}",
            external_idx=parsed_message_id,
            location=point,
            class_item=class_item,
            details=request.data.get("text") or "",
            user_id=str(request.data.get("author_id") or "") or None,
            status=MapEvent.STATUS_ACTIVE,
            confidence=float(request.data.get("confidence") or 0.7),
            confirmations=1,
            valid_until=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
            is_active=True,
        )
        return Response(MapEventDetailSerializer(event, context={"request": request}).data, status=201)

    @action(detail=False, methods=["post"], url_path="help-event")
    def help_event(self, request):
        """Создание технической точки на карте для сервиса взаимопомощи."""
        location = request.data.get("location") or {}
        coords = location.get("coordinates") if isinstance(location, dict) else None
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return Response({"detail": "location.coordinates is required"}, status=400)
        try:
            point = Point(float(coords[0]), float(coords[1]), srid=4326)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid coordinates"}, status=400)

        ttl_minutes = int(request.data.get("ttl_minutes") or 120)
        event = MapEvent.objects.create(
            source_kind=MapEvent.SOURCE_DYNAMIC,
            source="help",
            source_object_id="",
            location=point,
            class_item=None,
            details=request.data.get("description") or "",
            user_id=str(request.data.get("creator_user_id") or "") or None,
            status=MapEvent.STATUS_ACTIVE,
            is_active=True,
            valid_until=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
        )
        return Response(MapEventDetailSerializer(event, context={"request": request}).data, status=201)

    @action(detail=False, methods=["get"], url_path="processed-parsed-message-ids")
    def processed_parsed_message_ids(self, request):
        ids = (
            MapEvent.objects
            .filter(source="telegram", external_idx__isnull=False)
            .values_list("external_idx", flat=True)
            .distinct()
        )
        return Response({"ids": list(ids)})

    @action(detail=False, methods=["post"], url_path="expire-dynamic")
    def expire_dynamic(self, request):
        updated = MapEvent.objects.filter(
            source_kind=MapEvent.SOURCE_DYNAMIC,
            status__in=[MapEvent.STATUS_ACTIVE, MapEvent.STATUS_CONFIRMED],
            valid_until__lt=timezone.now(),
        ).update(status=MapEvent.STATUS_EXPIRED, is_active=False)
        return Response({"expired": updated})

    @action(detail=True, methods=["post"], url_path="vote")
    def vote(self, request, pk=None):
        """Голос за событие: один user_id может голосовать только один раз"""
        event = self.get_object()
        user_id = str(request.data.get("user_id") or "").strip()
        vote_value = int(request.data.get("vote") or 0)
        if not user_id:
            return Response({"detail": "user_id is required"}, status=400)
        if vote_value not in (1, -1):
            return Response({"detail": "vote must be 1 or -1"}, status=400)

        exists = EntityVote.objects.filter(
            event=event,
            user_id=user_id,
        ).exists()
        if exists:
            return Response({"detail": "User already voted for this event"}, status=409)

        lat = request.data.get("lat")
        lon = request.data.get("lon")
        voter_location = None
        if lat is not None and lon is not None:
            try:
                voter_location = Point(float(lon), float(lat), srid=4326)
            except (TypeError, ValueError):
                voter_location = None

        EntityVote.objects.create(
            event=event,
            user_id=user_id,
            vote=vote_value,
            voter_location=voter_location,
        )

        confirmations = EntityVote.objects.filter(
            event=event,
            vote=1,
        ).count()
        denials = EntityVote.objects.filter(
            event=event,
            vote=-1,
        ).count()
        balance = confirmations - denials
        new_status = event.status
        if balance >= 3:
            new_status = MapEvent.STATUS_CONFIRMED
        elif balance <= -3:
            new_status = MapEvent.STATUS_DENIED
        elif event.source_kind == MapEvent.SOURCE_DYNAMIC:
            new_status = MapEvent.STATUS_ACTIVE

        event.confirmations = confirmations
        event.denials = denials
        event.status = new_status
        event.save(update_fields=["confirmations", "denials", "status", "last_seen_at"])

        return Response({
            "confirmations": confirmations,
            "denials": denials,
            "status": event.status,
        }, status=201)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        """Архивировать событие: оставить в базе, но убрать с карты."""
        event = self.get_object()
        event.status = MapEvent.STATUS_ARCHIVED
        event.is_active = False
        event.save(update_fields=["status", "is_active", "last_seen_at"])
        return Response({
            "id": event.id,
            "status": event.status,
            "is_active": event.is_active,
        })

    # ========== MEDIA ==========

    @action(detail=True, methods=["post"], url_path="upload-media")
    def upload_media(self, request, pk=None):
        """Загрузка фото для события"""
        event = self.get_object()
        serializer = EventMediaUploadSerializer(
            data=request.data,
            context={"request": request, "event_id": event.id}
        )
        serializer.is_valid(raise_exception=True)
        media = serializer.save()
        return Response(EventMediaSerializer(media, context={"request": request}).data, status=201)

    @action(detail=True, methods=["delete"], url_path="delete-media/(?P<media_id>[^/.]+)")
    def delete_media(self, request, pk=None, media_id=None):
        """Удаление фото"""
        event = self.get_object()
        media = event.media.filter(id=media_id).first()
        if not media:
            return Response({"detail": "Media not found"}, status=404)
        media.delete()
        return Response(status=204)

    # ========== IMPORT ==========
    @action(detail=False, methods=["post"], url_path="import")
    def import_file(self, request):
        """Импорт PocketGIS файла"""
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)

        source_id = request.data.get("source_id")
        source = None
        source_name = ""

        if source_id:
            source = PocketGisSource.objects.filter(id=source_id).first()
            source_name = source.name if source else ""

        # Получаем маппинг категорий с фронта
        category_mapping = {}
        mapping_str = request.data.get("category_mapping", "{}")
        try:
            category_mapping = json.loads(mapping_str)
        except (json.JSONDecodeError, TypeError):
            pass

        import_row = PocketGisImport.objects.create(
            source=source,
            file_name=uploaded.name,
            status="running",
        )

        try:
            from events.services.pocketgis import parse_pocketgis_bytes

            raw_bytes = uploaded.read()
            parsed_rows, _, _ = parse_pocketgis_bytes(raw_bytes)

            insert_count = 0
            with transaction.atomic():
                for row in parsed_rows:
                    category_name = (row.category_name or "").strip()
                    
                    # Используем маппинг с фронта: category_name -> id EventClassItem
                    mapped_id = category_mapping.get(category_name)
                    class_item = None
                    if mapped_id:
                        class_item = EventClassItem.objects.filter(id=mapped_id).first()

                    MapEvent.objects.create(
                        source_kind=MapEvent.SOURCE_STATIC,
                        source="import",
                        source_name=source_name,
                        external_idx=row.external_idx,
                        source_object_id=f"pocketgis:{source_id or 'manual'}:{row.external_idx}",
                        location=Point(row.lon, row.lat, srid=4326),
                        class_item=class_item,
                        speed_limit=row.speed_limit or 0,
                        dir_type=row.dir_type or 1,
                        direction=row.direction or 0,
                        distance=row.distance or 0,
                        angle=row.angle or 0,
                        details=row.details or "",
                        is_active=True,
                        status=MapEvent.STATUS_CONFIRMED,
                    )
                    insert_count += 1

            import_row.status = "success"
            import_row.rows_total = len(parsed_rows)
            import_row.rows_inserted = insert_count
            import_row.finished_at = timezone.now()
            import_row.save()

            if source:
                source.last_sync_at = timezone.now()
                source.last_status = "success"
                source.save(update_fields=["last_sync_at", "last_status"])

            return Response(PocketGisImportSerializer(import_row).data)

        except Exception as exc:
            import_row.status = "failed"
            import_row.error_text = str(exc)
            import_row.finished_at = timezone.now()
            import_row.save()

            if source:
                source.last_status = "failed"
                source.save(update_fields=["last_status"])

            return Response({"detail": f"import failed: {exc}"}, status=400)

class EntityVoteViewSet(viewsets.ModelViewSet):
    """Голосование"""
    queryset = EntityVote.objects.select_related("event").all()
    serializer_class = EntityVoteSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        event_id = request.data.get("event") or request.data.get("event_id") or request.data.get("entity_id")
        user_id = str(request.data.get("user_id") or "").strip()
        vote_value = int(request.data.get("vote") or 0)
        if not event_id or not user_id:
            return Response({"detail": "event_id and user_id are required"}, status=400)
        if vote_value not in (1, -1):
            return Response({"detail": "vote must be 1 or -1"}, status=400)

        event = MapEvent.objects.filter(id=event_id).first()
        if not event:
            return Response({"detail": "Event not found"}, status=404)

        exists = EntityVote.objects.filter(
            event=event,
            user_id=user_id,
        ).exists()
        if exists:
            return Response({"detail": "User already voted for this event"}, status=409)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vote_obj = serializer.save(event=event, user_id=user_id)

        confirmations = EntityVote.objects.filter(event=event, vote=1).count()
        denials = EntityVote.objects.filter(event=event, vote=-1).count()
        balance = confirmations - denials
        if balance >= 3:
            status_value = MapEvent.STATUS_CONFIRMED
        elif balance <= -3:
            status_value = MapEvent.STATUS_DENIED
        elif event.source_kind == MapEvent.SOURCE_DYNAMIC:
            status_value = MapEvent.STATUS_ACTIVE
        else:
            status_value = event.status
        event.confirmations = confirmations
        event.denials = denials
        event.status = status_value
        event.save(update_fields=["confirmations", "denials", "status", "last_seen_at"])

        return Response(EntityVoteSerializer(vote_obj).data, status=201)


class PocketGisSourceViewSet(viewsets.ModelViewSet):
    """Источники импорта"""
    queryset = PocketGisSource.objects.all().order_by("name")
    serializer_class = PocketGisSourceSerializer
    permission_classes = [AllowAny]


class PocketGisImportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """История импортов"""
    queryset = PocketGisImport.objects.select_related("source").all().order_by("-created_at")
    serializer_class = PocketGisImportSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="convert")
    def convert(self, request):
        """Конвертация файла в CSV для предпросмотра"""
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)
        
        try:
            from events.services.pocketgis import parse_pocketgis_bytes
            raw_bytes = uploaded.read()
            parsed_rows, source_date, file_hash = parse_pocketgis_bytes(raw_bytes)
        except Exception as exc:
            return Response({"detail": f"convert failed: {exc}"}, status=400)
        
        import io, csv
        from pathlib import Path
        
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow([
            "IDX", "LON", "LAT", "TYPE", "CATEGORY",
            "SPEED_LIMIT", "DIR_TYPE", "DIRECTION", "DISTANCE", "ANGLE",
            "SOURCE_OBJECT_ID", "DETAILS", "SOURCE_DATE", "FILE_HASH"
        ])
        
        for row in parsed_rows:
            writer.writerow([
                row.external_idx, row.lon, row.lat, row.type_code,
                row.category_name, row.speed_limit, row.dir_type,
                row.direction, row.distance, row.angle,
                row.source_object_id, row.details, source_date, file_hash
            ])
        
        csv_text = buffer.getvalue()
        csv_bytes = ("\ufeff" + csv_text).encode("utf-8")
        in_name = Path(uploaded.name or "pocketgis").stem
        out_name = f"{in_name}_converted.csv"
        
        response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{out_name}"'
        return response
