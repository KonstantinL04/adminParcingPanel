#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import timedelta
from typing import Optional

import django
from django.utils import timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from events.models import ParsedMessage
from adminparcing.utils.nlp.NLPModel import match_location
from adminparcing.services.aggregator import process_parsed_message


def build_locations(text: str, chat_id: Optional[int]):
    matches = match_location(text, chat_id=chat_id)
    locations = []
    for place_name, lat, lon in matches:
        confidence = 0.6 if place_name == "автоопределено" else 0.9
        locations.append({
            "place_name": place_name,
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "confidence": confidence,
        })
    return locations


def process_messages(limit: Optional[int], since_minutes: Optional[int], reprocess: bool):
    qs = ParsedMessage.objects.all().order_by("created_at")
    if not reprocess:
        qs = qs.filter(roadevent__isnull=True)
    if since_minutes:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(minutes=since_minutes))
    if limit:
        qs = qs[:limit]

    total = 0
    created = 0
    for msg in qs:
        total += 1
        locations = build_locations(msg.text, msg.chat_id)
        if not locations:
            continue
        process_parsed_message(msg, locations)
        created += 1

    print(f"✅ Обработано сообщений: {total}, с локациями: {created}")


def process_new_messages():
    process_messages(limit=None, since_minutes=None, reprocess=False)


def main():
    parser = argparse.ArgumentParser(description="Определение локаций по спаршенным сообщениям")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить количество сообщений")
    parser.add_argument("--since-minutes", type=int, default=None, help="Только сообщения за N минут")
    parser.add_argument("--reprocess", action="store_true", help="Обрабатывать уже обработанные сообщения")
    args = parser.parse_args()

    process_messages(args.limit, args.since_minutes, args.reprocess)


if __name__ == "__main__":
    main()
