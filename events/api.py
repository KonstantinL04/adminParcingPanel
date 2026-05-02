from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point, Polygon
from django.http import HttpResponse
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
import csv
import io
from pathlib import Path
from .models import (
    ParsedMessage,
    RoadEvent,
    EventVote,
    PocketGisSource,
    PocketGisImport,
    PocketGisPoint,
    PocketGisCategory,
)
from .serializers import (
    ParsedMessageSerializer,
    RoadEventSerializer,
    RoadEventCreateSerializer,
    EventVoteSerializer,
    PocketGisSourceSerializer,
    PocketGisImportSerializer,
    PocketGisPointSerializer,
    PocketGisCategorySerializer,
)
from adminparcing.services.aggregator import process_parsed_message
from adminparcing.services.event_status import recalc_event_from_votes
from events.services.pocketgis import parse_pocketgis_bytes


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


class PocketGisSourceViewSet(ModelViewSet):
    queryset = PocketGisSource.objects.all().order_by("name")
    serializer_class = PocketGisSourceSerializer
    permission_classes = [AllowAny]


class PocketGisCategoryViewSet(ModelViewSet):
    queryset = PocketGisCategory.objects.all().order_by("sort_order", "name")
    serializer_class = PocketGisCategorySerializer
    permission_classes = [AllowAny]


class PocketGisImportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = PocketGisImport.objects.select_related("source").all().order_by("-created_at")
    serializer_class = PocketGisImportSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="convert")
    def convert(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)

        try:
            raw_bytes = uploaded.read()
            parsed_rows, source_date, file_hash = parse_pocketgis_bytes(raw_bytes)
        except Exception as exc:
            return Response({"detail": f"convert failed: {exc}"}, status=400)

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(
            [
                "IDX",
                "LON",
                "LAT",
                "TYPE",
                "CATEGORY",
                "SPEED_LIMIT",
                "DIR_TYPE",
                "DIRECTION",
                "DISTANCE",
                "ANGLE",
                "SOURCE_OBJECT_ID",
                "DETAILS",
                "SOURCE_DATE",
                "FILE_HASH",
            ]
        )

        for row in parsed_rows:
            writer.writerow(
                [
                    row.external_idx,
                    row.lon,
                    row.lat,
                    row.type_code,
                    row.category_name,
                    row.speed_limit,
                    row.dir_type,
                    row.direction,
                    row.distance,
                    row.angle,
                    row.source_object_id,
                    row.details,
                    source_date,
                    file_hash,
                ]
            )

        csv_text = buffer.getvalue()
        csv_bytes = ("\ufeff" + csv_text).encode("utf-8")
        in_name = Path(uploaded.name or "pocketgis").stem
        out_name = f"{in_name}_converted.csv"

        response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{out_name}"'
        return response

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required"}, status=400)

        source, _ = PocketGisSource.objects.get_or_create(
            name="OpenSpeedcam (manual import)",
            defaults={"enabled": True},
        )

        import_row = PocketGisImport.objects.create(
            source=source,
            file_name=uploaded.name,
            status="running",
        )

        try:
            raw_bytes = uploaded.read()
            parsed_rows, source_date, file_hash = parse_pocketgis_bytes(raw_bytes)
            # PocketGis file may contain duplicate external_idx rows.
            # Keep the last occurrence to avoid ON CONFLICT hitting same key twice.
            unique_rows_by_idx = {}
            for row in parsed_rows:
                unique_rows_by_idx[row.external_idx] = row
            parsed_rows = list(unique_rows_by_idx.values())
            import_row.source_date = source_date
            import_row.file_hash = file_hash
            import_row.rows_total = len(parsed_rows)

            existing_by_idx = {
                p.external_idx: p.id
                for p in PocketGisPoint.objects.filter(source=source).only("id", "external_idx")
            }

            def _normalized_category_name(value, type_code):
                base_name = (value or "").strip()
                if base_name:
                    return base_name
                return f"TYPE {type_code}"

            parsed_category_keys = {
                (r.type_code, _normalized_category_name(r.category_name, r.type_code))
                for r in parsed_rows
            }

            existing_categories = {
                (cat.type_code, cat.name): cat
                for cat in PocketGisCategory.objects.filter(
                    type_code__in=[k[0] for k in parsed_category_keys]
                )
            }

            missing_categories = [
                PocketGisCategory(type_code=type_code, name=name)
                for (type_code, name) in parsed_category_keys
                if (type_code, name) not in existing_categories
            ]
            if missing_categories:
                PocketGisCategory.objects.bulk_create(missing_categories, ignore_conflicts=True)
                existing_categories = {
                    (cat.type_code, cat.name): cat
                    for cat in PocketGisCategory.objects.filter(
                        type_code__in=[k[0] for k in parsed_category_keys]
                    )
                }

            from adminparcing.models import Region

            regions = list(Region.objects.exclude(boundary__isnull=True).only("id", "boundary"))

            def detect_region(point):
                for reg in regions:
                    if reg.boundary and reg.boundary.intersects(point):
                        return reg
                return None

            with transaction.atomic():
                rows_disabled = PocketGisPoint.objects.filter(source=source, is_active=True).update(is_active=False)
                to_upsert = []
                insert_count = 0
                update_count = 0

                for r in parsed_rows:
                    if r.external_idx in existing_by_idx:
                        update_count += 1
                    else:
                        insert_count += 1
                    point = Point(r.lon, r.lat, srid=4326)
                    region_obj = detect_region(point)
                    to_upsert.append(
                        PocketGisPoint(
                            source=source,
                            last_import=import_row,
                            category=existing_categories.get(
                                (r.type_code, _normalized_category_name(r.category_name, r.type_code))
                            ),
                            region=region_obj,
                            city=None,
                            external_idx=r.external_idx,
                            source_object_id=r.source_object_id,
                            location=point,
                            type_code=r.type_code,
                            speed_limit=r.speed_limit,
                            dir_type=r.dir_type,
                            direction=r.direction,
                            distance=r.distance,
                            angle=r.angle,
                            details=r.details,
                            is_active=True,
                        )
                    )

                PocketGisPoint.objects.bulk_create(
                    to_upsert,
                    update_conflicts=True,
                    update_fields=[
                        "last_import",
                        "category",
                        "region",
                        "city",
                        "source_object_id",
                        "location",
                        "type_code",
                        "speed_limit",
                        "dir_type",
                        "direction",
                        "distance",
                        "angle",
                        "details",
                        "is_active",
                        "last_seen_at",
                    ],
                    unique_fields=["source", "external_idx"],
                )

            import_row.status = "success"
            import_row.rows_inserted = insert_count
            import_row.rows_updated = update_count
            import_row.rows_disabled = rows_disabled
            import_row.finished_at = timezone.now()
            import_row.save(
                update_fields=[
                    "source_date",
                    "file_hash",
                    "rows_total",
                    "status",
                    "rows_inserted",
                    "rows_updated",
                    "rows_disabled",
                    "finished_at",
                ]
            )

            source.last_sync_at = timezone.now()
            source.last_status = "success"
            source.save(update_fields=["last_sync_at", "last_status"])
            return Response(PocketGisImportSerializer(import_row).data)
        except Exception as exc:
            import_row.status = "failed"
            import_row.error_text = str(exc)
            import_row.finished_at = timezone.now()
            import_row.save(update_fields=["status", "error_text", "finished_at"])
            source.last_status = "failed"
            source.save(update_fields=["last_status"])
            return Response({"detail": f"import failed: {exc}"}, status=400)


class PocketGisPointViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = PocketGisPointSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            PocketGisPoint.objects
            .filter(is_active=True)
            .select_related("category", "source", "region", "city")
            .only(
                "id",
                "location",
                "category_id",
                "speed_limit",
                "direction",
                "distance",
                "angle",
                "region_id",
                "last_seen_at",
                "category__name",
                "category__icon",
                "source__name",
                "region__name",
                "city__name",
            )
        )
        region = self.request.query_params.get("region")
        source = self.request.query_params.get("source")
        category = self.request.query_params.get("category")
        search = (self.request.query_params.get("search") or "").strip()
        bbox = (self.request.query_params.get("bbox") or "").strip()

        if region:
            qs = qs.filter(region_id=region)
        if source:
            qs = qs.filter(source_id=source)
        if category:
            if "," in category:
                ids = [x.strip() for x in category.split(",") if x.strip()]
                qs = qs.filter(category_id__in=ids)
            else:
                qs = qs.filter(category_id=category)
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
        qs = self.get_queryset()
        limit = int(request.query_params.get("limit", 500))
        offset = int(request.query_params.get("offset", 0))
        limit = min(max(limit, 1), 5000)
        offset = max(offset, 0)
        items = qs[offset : offset + limit]
        data = PocketGisPointSerializer(items, many=True).data
        return Response(
            {
                "limit": limit,
                "offset": offset,
                "results": data,
            }
        )
