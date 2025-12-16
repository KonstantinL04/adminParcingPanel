import requests
from django.conf import settings
import os
EVENTS_API_URL = os.getenv("EVENTS_API_URL")

def send_parsed_message(data: dict):
    r = requests.post(
        f"{EVENTS_API_URL}/messages/",
        json=data,
        timeout=5
    )
    r.raise_for_status()