import requests
from django.conf import settings


EVENTS_API_URL = getattr(settings, "EVENTS_SERVICE_URL", "http://localhost:8000/api/events").rstrip("/")


def get_events_in_bbox(*, min_lon, min_lat, max_lon, max_lat, limit=500):
    response = requests.get(
        f"{EVENTS_API_URL}/events/",
        params={
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "limit": limit,
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("results") if isinstance(data, dict) else data
