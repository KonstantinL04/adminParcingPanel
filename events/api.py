# api.py

import json

from django.db import models as django_models
from django.db import transaction
from django.contrib.gis.geos import Point, Polygon
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
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
    HelpRequest,
    HelpRequestResponse,
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
    HelpRequestSerializer,
    HelpRequestResponseSerializer,
    HelpRequestRespondSerializer,
    HelpRequestAcceptSerializer,
    EntityVoteSerializer,
    PocketGisSourceSerializer,
    PocketGisImportSerializer,
)


class EventClassViewSet(viewsets.ModelViewSet):
    """Классы событий"""
    queryset = EventClass.objects.filter(enabled=True).order_by("sort_order", "name")
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
    queryset = EventClassItem.objects.filter(enabled=True).select_related("event_class").order_by(
        "event_class__sort_order", "sort_order", "name"
    )
    serializer_class = EventClassItemSerializer
    permission_classes = [AllowAny]


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

    # ========== HELP REQUEST ==========

    @action(detail=True, methods=["get"], url_path="help-request")
    def get_help_request(self, request, pk=None):
        """Получить информацию о запросе помощи"""
        event = self.get_object()
        hr = getattr(event, 'help_request', None)
        if not hr:
            return Response({"detail": "Not a help request"}, status=404)
        serializer = HelpRequestSerializer(hr, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="help-respond")
    def help_respond(self, request, pk=None):
        """Откликнуться на запрос помощи"""
        event = self.get_object()
        hr = getattr(event, 'help_request', None)

        if not hr:
            return Response({"detail": "Not a help request"}, status=400)
        if hr.status != HelpRequest.STATUS_ACTIVE:
            return Response({"detail": f"Help request is {hr.status}"}, status=400)

        serializer = HelpRequestRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        message = serializer.validated_data.get("message", "")

        response, created = HelpRequestResponse.objects.get_or_create(
            help_request=hr,
            responder_user_id=user_id,
            defaults={"message": message}
        )

        if created:
            hr.status = HelpRequest.STATUS_IN_PROGRESS
            hr.save(update_fields=["status"])

        return Response(HelpRequestResponseSerializer(response).data, status=201 if created else 200)

    @action(detail=True, methods=["post"], url_path="help-accept")
    def help_accept(self, request, pk=None):
        """Принять отклик (только создатель запроса)"""
        event = self.get_object()
        hr = getattr(event, 'help_request', None)

        if not hr:
            return Response({"detail": "Not a help request"}, status=400)

        serializer = HelpRequestAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_id = serializer.validated_data["response_id"]
        response = hr.responses.filter(id=response_id).first()

        if not response:
            return Response({"detail": "Response not found"}, status=404)

        # Принимаем отклик
        response.accepted = True
        response.save(update_fields=["accepted"])

        # Закрываем запрос
        hr.status = HelpRequest.STATUS_COMPLETED
        hr.closed_at = timezone.now()
        hr.save(update_fields=["status", "closed_at"])

        # Деактивируем событие на карте
        event.is_active = False
        event.save(update_fields=["is_active"])

        return Response({
            "status": "accepted",
            "responder_user_id": response.responder_user_id,
        })

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
    queryset = EntityVote.objects.all()
    serializer_class = EntityVoteSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        request = self.request
        entity_type = request.data.get("entity_type", "mapevent")
        entity_id = request.data.get("entity_id")

        content_type = ContentType.objects.get(
            app_label="events",
            model=entity_type if entity_type != "roadevent" else "mapevent"
        )

        serializer.save(
            content_type=content_type,
            object_id=entity_id,
        )


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