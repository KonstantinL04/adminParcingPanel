from datetime import timedelta

from django.utils import timezone

from adminparcing.models import AlertCategory
from events.models import RoadEvent

DEFAULT_TTL_MINUTES = 60


def _get_category(category_id, category_name):
    if category_id:
        cat = AlertCategory.objects.filter(id=category_id).first()
        if cat:
            return cat
    if category_name:
        cat = AlertCategory.objects.filter(name=category_name).first()
        if cat:
            return cat
    return None


def get_ttl_minutes(category_id, category_name) -> int:
    cat = _get_category(category_id, category_name)
    return cat.ttl_minutes if cat else DEFAULT_TTL_MINUTES


def get_thresholds(category_id, category_name):
    cat = _get_category(category_id, category_name)
    if cat:
        return cat.confirm_threshold, cat.deny_threshold
    return 3, -3


def recalc_event_from_votes(event: RoadEvent):
    ttl_minutes = get_ttl_minutes(event.category_id, event.category_label)
    window_start = timezone.now() - timedelta(minutes=ttl_minutes)
    votes = event.votes.filter(created_at__gte=window_start).values_list("vote", flat=True)
    confirmations = sum(votes) if votes else 0

    event.confirmations = confirmations
    confirm_threshold, deny_threshold = get_thresholds(event.category_id, event.category_label)
    if confirmations >= confirm_threshold:
        event.status = "confirmed"
    elif confirmations <= deny_threshold:
        event.status = "denied"
    else:
        event.status = "active"

    event.valid_until = timezone.now() + timedelta(minutes=ttl_minutes)
    event.save(update_fields=["confirmations", "status", "valid_until"])


def expire_events():
    now = timezone.now()
    RoadEvent.objects.filter(
        status__in=["active", "confirmed"],
        valid_until__lt=now
    ).update(status="expired")
