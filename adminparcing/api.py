from rest_framework.viewsets import GenericViewSet
from adminparcing.models import Chat, ExcludedUser, AlertCategory, Region, City, Location, RoutePoint, Route, Setting, SettingAPI
from rest_framework import mixins, viewsets
from adminparcing.serializers import ChatSerializer, ExcludedUserSerializer, AlertCategorySerializer, RegionSerializer, CitySerializer, LocationSerializer, RoutePointSerializer, RouteCreateSerializer, RouteSerializer, SettingSerializer, SettingAPISerializer
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
import json

from adminparcing.utils.telegram.parsing_controller import parser_controller
from adminparcing.utils.nlp.train_model import train_for_chat, train_all


def _looks_like_highcharts_coords(geometry):
    coords = geometry.get("coordinates")
    if not isinstance(coords, list):
        return False

    points = []

    def walk(node):
        if isinstance(node, list):
            if len(node) == 2 and all(isinstance(v, (int, float)) for v in node):
                points.append(node)
                return
            for item in node:
                walk(item)

    walk(coords)
    if not points:
        return False

    # Highcharts map files often contain projected-like values (millions),
    # while real WGS84 lon/lat are within +-180/+-90.
    big_values = sum(1 for x, y in points[:1000] if abs(x) > 180 or abs(y) > 90)
    return big_values > 0


def _convert_regions_latlon_json_to_features(payload):
    # Supported input:
    # {
    #   "Алтайский край": {
    #     "0": [[lat, lon], ...],
    #     "1": [[lat, lon], ...]
    #   },
    #   ...
    # }
    if not isinstance(payload, dict) or "features" in payload:
        return None

    features = []
    for region_name, polygons_obj in payload.items():
        if not isinstance(region_name, str) or not isinstance(polygons_obj, dict):
            continue

        polygons = []
        for _, ring_points in polygons_obj.items():
            if not isinstance(ring_points, list) or len(ring_points) < 3:
                continue

            ring = []
            for pair in ring_points:
                if not (isinstance(pair, list) and len(pair) == 2):
                    continue
                lat, lon = pair[0], pair[1]
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                    continue
                ring.append([float(lon), float(lat)])

            if len(ring) < 3:
                continue
            if ring[0] != ring[-1]:
                ring.append(ring[0])

            polygons.append([ring])  # polygon with one outer ring

        if not polygons:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": {"name": region_name},
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )

    return features


def _extract_region_name(properties):
    if not isinstance(properties, dict):
        return ""
    keys = (
        "name",
        "NAME",
        "region",
        "region_name",
        "shapeName",
        "shape_name",
        "NAME_1",
        "ADM1_EN",
        "ADM1_RU",
    )
    for key in keys:
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_city_name(properties):
    if not isinstance(properties, dict):
        return ""
    keys = (
        "name",
        "NAME",
        "city",
        "city_name",
        "shapeName",
        "shape_name",
    )
    for key in keys:
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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

    @action(detail=False, methods=["post"], url_path="upload_geojson")
    def upload_geojson(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)

        try:
            payload = json.loads(uploaded.read().decode("utf-8-sig"))
        except Exception as exc:
            return Response({"detail": f"invalid geojson: {exc}"}, status=400)

        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            # Fallback for custom region->polygons JSON format.
            features = _convert_regions_latlon_json_to_features(payload)
        if not isinstance(features, list):
            return Response(
                {"detail": "Нужен GeoJSON FeatureCollection или JSON вида {\"Область\": {\"0\": [[lat, lon], ...]}}"},
                status=400,
            )

        created = 0
        updated = 0
        skipped = 0

        for feature in features:
            geometry = (feature or {}).get("geometry")
            properties = (feature or {}).get("properties") or {}
            name = _extract_region_name(properties)
            if not name or not geometry:
                skipped += 1
                continue
            try:
                if _looks_like_highcharts_coords(geometry):
                    return Response(
                        {
                            "detail": "Файл содержит координаты не в WGS84 (похоже на Highcharts-проекцию). Нужен GeoJSON с обычными lon/lat (EPSG:4326)."
                        },
                        status=400,
                    )
                geom = GEOSGeometry(json.dumps(geometry), srid=4326)
                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom, srid=4326)
                elif geom.geom_type != "MultiPolygon":
                    skipped += 1
                    continue
            except Exception:
                skipped += 1
                continue

            obj, was_created = Region.objects.update_or_create(
                name=str(name).strip(),
                defaults={"boundary": geom},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response(
            {
                "status": "ok",
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "total_features": len(features),
            }
        )

class CityViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = City.objects.select_related("region").all()
    serializer_class = CitySerializer

    @action(detail=False, methods=["post"], url_path="upload_geojson")
    def upload_geojson(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)

        try:
            payload = json.loads(uploaded.read().decode("utf-8-sig"))
        except Exception as exc:
            return Response({"detail": f"invalid geojson: {exc}"}, status=400)

        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            return Response({"detail": "GeoJSON FeatureCollection is required"}, status=400)

        regions = list(Region.objects.exclude(boundary__isnull=True))
        created = 0
        updated = 0
        skipped = 0

        for feature in features:
            geometry = (feature or {}).get("geometry")
            properties = (feature or {}).get("properties") or {}
            name = _extract_city_name(properties)
            if not name or not geometry:
                skipped += 1
                continue

            try:
                if _looks_like_highcharts_coords(geometry):
                    return Response(
                        {
                            "detail": "Файл содержит координаты не в WGS84 (похоже на Highcharts-проекцию). Нужен GeoJSON с обычными lon/lat (EPSG:4326)."
                        },
                        status=400,
                    )
                geom = GEOSGeometry(json.dumps(geometry), srid=4326)
                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom, srid=4326)
                elif geom.geom_type != "MultiPolygon":
                    skipped += 1
                    continue
            except Exception:
                skipped += 1
                continue

            region = None
            region_id = properties.get("region_id")
            region_name = (
                properties.get("region")
                or properties.get("region_name")
                or properties.get("REGION")
            )

            if region_id:
                region = Region.objects.filter(id=region_id).first()
            if not region and region_name:
                region = Region.objects.filter(name__iexact=str(region_name).strip()).first()
            if not region:
                centroid = geom.centroid
                for r in regions:
                    if r.boundary and r.boundary.intersects(centroid):
                        region = r
                        break
            if not region:
                skipped += 1
                continue

            obj, was_created = City.objects.update_or_create(
                region=region,
                name=str(name).strip(),
                defaults={"boundary": geom},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response(
            {
                "status": "ok",
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "total_features": len(features),
            }
        )
    
class LocationViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin, 
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  GenericViewSet):
    queryset = (
        Location.objects
        .select_related("chat", "city", "city__region")
        .prefetch_related("chats")
        .order_by("-created_at", "-id")
    )
    serializer_class = LocationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        chat_ids_raw = self.request.query_params.get("chat_ids", "")
        if not chat_ids_raw:
            return qs

        chat_ids = []
        for token in chat_ids_raw.split(","):
            token = (token or "").strip()
            if token.isdigit():
                chat_ids.append(int(token))
        if not chat_ids:
            return qs

        return qs.filter(Q(chat_id__in=chat_ids) | Q(chats__id__in=chat_ids)).distinct().order_by("-created_at", "-id")
 
class RouteViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   GenericViewSet):
    queryset = Route.objects.prefetch_related("chats", "points", "points__location")

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
