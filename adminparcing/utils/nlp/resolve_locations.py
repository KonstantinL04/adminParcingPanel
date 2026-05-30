#!/usr/bin/env python3
import os
import sys
import argparse
import re
from datetime import timedelta
from typing import Optional

import django
from django.utils import timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from adminparcing.models import Location, ParsedMessage, Setting
from adminparcing.services.event_client import get_processed_parsed_message_ids
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


NOISE_PHRASES = [
    "в обе стороны",
    "в обе сторон",
    "в сторону",
    "в направлении",
    "по направлению",
    "в город",
    "из города",
    "из центра",
    "в центр",
    "по городу",
    "на выезд",
    "на въезд",
]

NOISE_WORDS = {
    "актив",
    "актуально",
    "внимание",
    "работают",
    "стоят",
    "движение",
    "направление",
    "сторону",
    "стороны",
    "обе",
    "обратно",
    "туда",
    "сюда",
    "дтп",
    "авария",
    "камера",
    "дпс",
    "чисто",
    "перекрытие",
    "пробка",
    "рейд",
    "пост",
}

GENERIC_PLACE_NAMES = {
    "город",
    "центр",
    "выезд",
    "въезд",
    "трасса",
    "дорога",
    "улица",
    "район",
}


def clean_place_candidate(raw: str) -> Optional[str]:
    if not raw:
        return None

    cleaned = raw.replace("ё", "е").lower()
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"[\"'`«»]", " ", cleaned)
    for phrase in NOISE_PHRASES:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s\-]", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    words = []
    for w in cleaned.split():
        if w in NOISE_WORDS:
            continue
        if w.isdigit():
            continue
        if len(w) < 2:
            continue
        words.append(w)

    if not words:
        return None

    # Локации из словаря обычно короткие; ограничиваем длину, чтобы не тащить "мусор".
    words = words[:4]
    candidate = " ".join(words).strip()
    if len(candidate) < 3:
        return None
    if candidate in GENERIC_PLACE_NAMES:
        return None
    return candidate


def strip_category_markers(source: str, msg: ParsedMessage) -> str:
    if not msg.parsing_category_id:
        return source

    try:
        rule = msg.parsing_category
    except Exception:
        rule = None

    cleaned = source
    text_patterns = getattr(rule, "text_patterns", None) or []
    emoji_patterns = getattr(rule, "emoji_patterns", None) or []

    for marker in [*text_patterns, *emoji_patterns]:
        marker_text = str(marker or "").replace("ё", "е").strip().lower()
        if not marker_text:
            continue
        if re.search(r"\w", marker_text, flags=re.UNICODE):
            pattern = rf"(?<!\w){re.escape(marker_text)}(?!\w)"
        else:
            pattern = re.escape(marker_text)
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_candidate_place_name(text: str, msg: ParsedMessage) -> Optional[str]:
    if not text:
        return None

    source = text
    if "| Ответ:" in source:
        source = source.split("| Ответ:", 1)[1]
    source = re.sub(r"\s+", " ", source).strip()
    source = source.replace("ё", "е").lower()
    source = strip_category_markers(source, msg)
    if not source:
        return None

    patterns = [
        r"\b(?:на|у|в|во|возле|около|рядом с|перед|после|напротив|в районе|район)\s+([^,.;!?]{2,70})",
        r"\b(?:от|до|между)\s+([^,.;!?]{2,70})",
    ]

    candidates = []
    for pattern in patterns:
        for raw in re.findall(pattern, source, flags=re.IGNORECASE):
            name = clean_place_candidate(raw)
            if name:
                candidates.append(name)

    # Фолбэк: пробуем использовать начало сообщения после грубой очистки.
    if not candidates:
        fallback = clean_place_candidate(source[:80])
        if fallback:
            candidates.append(fallback)

    if not candidates:
        return None
    return sorted(candidates, key=lambda x: (len(x.split()), len(x)), reverse=True)[0]


def load_unresolved_category_filter() -> Optional[set[int]]:
    raw = (
        Setting.objects.filter(key="unresolved_location_category_ids")
        .values_list("value", flat=True)
        .first()
    )
    if raw is None:
        return None

    value = (raw or "").strip().lower()
    if not value:
        return None
    if value in {"none", "off", "disable", "disabled", "0"}:
        return set()

    selected = set()
    for part in re.split(r"[\s,;]+", value):
        if not part:
            continue
        if part.isdigit():
            selected.add(int(part))
    return selected


def ensure_unresolved_location_stub(msg: ParsedMessage, allowed_categories: Optional[set[int]]):
    category_id = msg.parsing_category.category_id if msg.parsing_category else None
    if allowed_categories is not None:
        if not allowed_categories:
            return False
        if not category_id or category_id not in allowed_categories:
            return False

    candidate = extract_candidate_place_name(msg.text or "", msg)
    if not candidate or not msg.chat_id:
        return False

    exists = (
        Location.objects
        .filter(name__iexact=candidate)
        .filter(chats__id=msg.chat_id)
        .distinct()
        .exists()
    )
    if exists:
        return False

    location = Location.objects.create(
        name=candidate,
        city=getattr(msg.chat, "city", None),
        synonyms=[],
        location=None,
    )
    location.chats.add(msg.chat_id)
    print(f"🆕 Добавлено место без координат в словарь: '{candidate}' (chat_id={msg.chat_id})")
    return True


def process_messages(limit: Optional[int], since_minutes: Optional[int], reprocess: bool):
    qs = ParsedMessage.objects.all().order_by("created_at")
    if not reprocess:
        processed_ids = get_processed_parsed_message_ids()
        if processed_ids:
            qs = qs.exclude(id__in=processed_ids)
    if since_minutes:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(minutes=since_minutes))
    if limit:
        qs = qs[:limit]

    total = 0
    created = 0
    unresolved_added = 0
    allowed_categories = load_unresolved_category_filter()
    for msg in qs:
        total += 1
        locations = build_locations(msg.text, msg.chat_id)
        if not locations:
            if ensure_unresolved_location_stub(msg, allowed_categories):
                unresolved_added += 1
            continue
        process_parsed_message(msg, locations)
        created += 1

    print(
        "✅ Обработано сообщений: "
        f"{total}, с локациями: {created}, добавлено мест без координат: {unresolved_added}"
    )


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
