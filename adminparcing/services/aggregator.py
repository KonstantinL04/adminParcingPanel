from adminparcing.services.event_client import create_or_update_event_from_parsed

MAX_DISTANCE_METERS = 50


def process_parsed_message(parsed_message, locations):
    if not locations:
        return

    parsing_category = parsed_message.parsing_category
    for loc in locations:
        coordinates = (loc.get("location") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue
        create_or_update_event_from_parsed({
            "parsed_message_id": parsed_message.id,
            "telegram_message_id": parsed_message.telegram_message_id,
            "category_id": parsing_category.category_id if parsing_category else None,
            "category_name": parsing_category.category_name if parsing_category else "",
            "text": parsed_message.text or "",
            "chat_id": parsed_message.chat_id,
            "chat_title": parsed_message.chat.title if parsed_message.chat_id else "",
            "author_id": parsed_message.author_id,
            "author_name": parsed_message.author_name or "",
            "created_at": parsed_message.created_at.isoformat() if parsed_message.created_at else None,
            "lon": coordinates[0],
            "lat": coordinates[1],
            "place_name": loc.get("place_name", ""),
            "source": loc.get("source", "nlp"),
            "confidence": loc.get("confidence", 0.7),
            "dedup_radius_m": MAX_DISTANCE_METERS,
        })
