import requests
from django.conf import settings


EVENTS_API_URL = getattr(settings, "EVENTS_SERVICE_URL", "http://localhost:8000/api/events").rstrip("/")


def _request(method, path, **kwargs):
    url = f"{EVENTS_API_URL}/{path.lstrip('/')}"
    response = requests.request(method, url, timeout=5, **kwargs)
    response.raise_for_status()
    if not response.content:
        return None
    return response.json()


def get_event_category(category_id):
    if not category_id:
        return None
    try:
        return _request("get", f"event-class-items/{int(category_id)}/")
    except Exception as exc:
        print(f"Ошибка получения категории события #{category_id}: {exc}")
        return None


def create_or_update_event_from_parsed(payload):
    try:
        return _request("post", "events/from-parsed/", json=payload)
    except Exception as exc:
        print(f"Ошибка отправки результата парсинга в сервис дорожных событий: {exc}")
        return None


def get_processed_parsed_message_ids():
    try:
        data = _request("get", "events/processed-parsed-message-ids/")
    except Exception as exc:
        print(f"Ошибка получения обработанных сообщений из сервиса дорожных событий: {exc}")
        return set()
    return set(data.get("ids") or [])


def expire_dynamic_events():
    try:
        return _request("post", "events/expire-dynamic/")
    except Exception as exc:
        print(f"Ошибка автоархивации событий в сервисе дорожных событий: {exc}")
        return None


def send_parsed_message(payload):
    return create_or_update_event_from_parsed(payload)
