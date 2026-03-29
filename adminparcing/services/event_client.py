# import requests
# from django.conf import settings
# import os
# EVENTS_API = "http://localhost:8000/api/events/messages/"

# def send_parsed_message(payload: dict):
#     try:
#         r = requests.post(EVENTS_API, json=payload, timeout=5)
#         r.raise_for_status()
#     except Exception as e:
#         print("❌ Ошибка отправки в events:", e)
import requests

API_URL = "http://localhost:8000/api/events/messages/"

def send_parsed_message(payload: dict):
    try:
        r = requests.post(API_URL, json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Ошибка отправки ParsedMessage: {e}")