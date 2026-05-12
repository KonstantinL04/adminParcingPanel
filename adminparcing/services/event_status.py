from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from events.models import EntityVote, MapEvent, EventClassItem

DEFAULT_TTL_MINUTES = 60


def _get_category(category_id, category_name):
    if category_id:
        item = EventClassItem.objects.filter(id=category_id).first()
        if item:
            return item
    if category_name:
        item = EventClassItem.objects.filter(name=category_name).first()
        if item:
            return item
    return None


def get_ttl_minutes(category_id, category_name) -> int:
    cat = _get_category(category_id, category_name)
    return getattr(cat, "ttl_minutes", DEFAULT_TTL_MINUTES) if cat else DEFAULT_TTL_MINUTES


def recalc_event_from_votes(event: MapEvent):
    ttl_minutes = get_ttl_minutes(event.category_id, event.category_label)
    window_start = timezone.now() - timedelta(minutes=ttl_minutes)
    event_content_type = ContentType.objects.get_for_model(MapEvent)
    votes = EntityVote.objects.filter(
        content_type=event_content_type,
        object_id=event.id,
        created_at__gte=window_start,
    ).values_list("vote", flat=True)
    confirmations = sum(votes) if votes else 0

    event.confirmations = confirmations
    confirm_threshold, deny_threshold = 3, -3
    if confirmations >= confirm_threshold:
        event.status = MapEvent.STATUS_CONFIRMED
    elif confirmations <= deny_threshold:
        event.status = MapEvent.STATUS_DENIED
    else:
        event.status = MapEvent.STATUS_ACTIVE

    event.valid_until = timezone.now() + timedelta(minutes=ttl_minutes)
    event.save(update_fields=["confirmations", "status", "valid_until"])


def expire_events():
    now = timezone.now()
    MapEvent.objects.filter(
        source_kind=MapEvent.SOURCE_DYNAMIC,
        status__in=[MapEvent.STATUS_ACTIVE, MapEvent.STATUS_CONFIRMED],
        valid_until__lt=now
    ).update(status=MapEvent.STATUS_EXPIRED)
