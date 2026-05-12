from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils import timezone
from events.models import MapEvent
from adminparcing.services.event_status import get_ttl_minutes

MAX_DISTANCE_METERS = 50
EVENT_TTL_MINUTES = 60


def process_parsed_message(parsed_message, locations):
    if not locations:
        return

    category = getattr(parsed_message, "category", None)
    category_id = parsed_message.category_id or 0
    category_name = category.name if category else ""

    for loc in locations:
        point = Point(
            loc["location"]["coordinates"][0],
            loc["location"]["coordinates"][1],
            srid=4326
        )

        # Ищем существующее событие рядом ТОЛЬКО той же категории.
        # События разных категорий должны существовать независимо.
        event = (
            MapEvent.objects
            .filter(
                source_kind=MapEvent.SOURCE_DYNAMIC,
                status__in=[MapEvent.STATUS_ACTIVE, MapEvent.STATUS_CONFIRMED],
                category_id=category_id,
                location__distance_lte=(point, D(m=MAX_DISTANCE_METERS))
            )
            .order_by("-last_activity_at")
            .first()
        )

        if event:
            # подтверждаем существующее только если сообщение новее
            if parsed_message.created_at and parsed_message.created_at <= event.last_activity_at:
                continue
            event.confirmations += 1
            event.confidence = min(1.0, event.confidence + 0.1)
            event.last_activity_at = parsed_message.created_at
            event.save(update_fields=["confirmations", "confidence", "last_activity_at"])
        if not event:
            # создаём новое событие
            ttl_minutes = get_ttl_minutes(category_id, category_name)
            MapEvent.objects.create(
                source_kind=MapEvent.SOURCE_DYNAMIC,
                source_message=parsed_message,
                location=point,
                category_id=category_id,
                category_code=category_name,
                category_label=category_name,
                extra_params={
                    "telegram_message_id": parsed_message.telegram_message_id,
                    "place_name": loc.get("place_name", ""),
                    "source": loc.get("source", "nlp"),
                    "author_name": parsed_message.author_name or "",
                },
                user_id=str(parsed_message.author_id) if parsed_message.author_id is not None else None,
                status=MapEvent.STATUS_ACTIVE,
                confidence=loc.get("confidence", 0.7),
                confirmations=1,
                valid_until=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
                source="telegram",
                is_active=True,
            )
