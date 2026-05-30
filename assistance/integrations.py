import requests
from django.conf import settings
from django.contrib.gis.geos import Point


EVENTS_API_URL = getattr(settings, "EVENTS_SERVICE_URL", "http://localhost:8000/api/events").rstrip("/")
ACCOUNTS_API_URL = getattr(settings, "ACCOUNTS_SERVICE_URL", "http://localhost:8000/api/accounts").rstrip("/")


def _request(method, url, **kwargs):
    response = requests.request(method, url, timeout=5, **kwargs)
    response.raise_for_status()
    if not response.content:
        return None
    return response.json()


def create_help_map_event(*, location, description, creator_user_id, ttl_minutes):
    data = _request(
        "post",
        f"{EVENTS_API_URL}/events/help-event/",
        json={
            "location": {
                "type": "Point",
                "coordinates": [location.x, location.y],
            },
            "description": description,
            "creator_user_id": creator_user_id,
            "ttl_minutes": ttl_minutes,
        },
    )
    return data or {}


def close_help_map_event(event_id):
    if not event_id:
        return None
    try:
        return _request("post", f"{EVENTS_API_URL}/events/{event_id}/archive/")
    except Exception:
        return None


def apply_helper_rating(*, helper_user_id, solved, rating_delta, rating_comment, source_object):
    action = "help_completed" if solved else "help_failed"
    try:
        return _request(
            "post",
            f"{ACCOUNTS_API_URL}/reputation/apply/",
            json={
                "user_id": int(helper_user_id),
                "action": action,
                "reputation_delta": int(rating_delta),
                "comment": rating_comment,
            },
        )
    except Exception:
        return None


def make_point(lon, lat):
    return Point(float(lon), float(lat), srid=4326)
