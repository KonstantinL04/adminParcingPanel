import requests
from django.conf import settings


EVENTS_API_URL = getattr(settings, "EVENTS_SERVICE_URL", "http://localhost:8000/api/events").rstrip("/")
ACCOUNTS_API_URL = getattr(settings, "ACCOUNTS_SERVICE_URL", "http://localhost:8000/api/accounts").rstrip("/")


def _request(method, url, **kwargs):
    response = requests.request(method, url, timeout=5, **kwargs)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    if not response.content:
        return None
    return response.json()


def get_event(event_id):
    return _request("get", f"{EVENTS_API_URL}/events/{event_id}/")


def patch_event(event_id, payload):
    return _request("patch", f"{EVENTS_API_URL}/events/{event_id}/", json=payload)


def archive_event(event_id):
    return _request("post", f"{EVENTS_API_URL}/events/{event_id}/archive/")


def get_user(user_id):
    return _request("get", f"{ACCOUNTS_API_URL}/users/{user_id}/")


def patch_user(user_id, payload):
    return _request("patch", f"{ACCOUNTS_API_URL}/users/{user_id}/", json=payload)


def patch_user_profile(user_id, payload):
    return _request("patch", f"{ACCOUNTS_API_URL}/profiles/by-user/{user_id}/", json=payload)
