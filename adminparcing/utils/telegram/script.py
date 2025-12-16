#!/usr/bin/env python3

import os
import re
import base64
import asyncio
import tempfile
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import django
from dotenv import load_dotenv
from telethon import TelegramClient, events, functions
from telethon.errors import SessionPasswordNeededError
import websockets
import json


# ─────────────────────────────────────────────────────────────
# Django setup
# ─────────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from adminparcing.models import Chat, AlertCategory, ExcludedUser, Location, SettingAPI
from adminparcing.utils.nlp.NLPModel import match_location
from adminparcing.services.event_client import send_parsed_message

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
load_dotenv()

def load_api_credentials():
    api_id = int(SettingAPI.objects.get(key="API_ID").value)
    api_hash = SettingAPI.objects.get(key="API_HASH").value
    session_name = SettingAPI.objects.get(key="SESSION_NAME").value
    return api_id, api_hash, session_name

API_ID, API_HASH, SESSION_NAME = load_api_credentials()

# ─────────────────────────────────────────────────────────────
# Timezone
# ─────────────────────────────────────────────────────────────
LOCAL_OFFSET_ENV = os.getenv("LOCAL_OFFSET")
LOCAL_TZ = timezone(timedelta(hours=int(LOCAL_OFFSET_ENV))) if LOCAL_OFFSET_ENV else datetime.now().astimezone().tzinfo

# ─────────────────────────────────────────────────────────────
# Runtime buffers
# ─────────────────────────────────────────────────────────────
GEO_TTL_SECONDS = 300
last_location_by_user: Dict[int, Dict[str, Any]] = {}
recent_unclassified_by_chat: Dict[Any, List[Dict[str, Any]]] = {}
last_classified_by_author: Dict[tuple, Dict[str, Any]] = {}

# ─────────────────────────────────────────────────────────────
# Bootstrap data
# ─────────────────────────────────────────────────────────────
def load_target_chats():
    result = []
    for c in Chat.objects.filter(enabled=True):
        try:
            result.append(int(c.chat_id))
        except ValueError:
            result.append(c.chat_id)
    return result

def load_excluded_users():
    res = set()
    for u in ExcludedUser.objects.all():
        res.add(int(u.value) if u.value.isdigit() else u.value.lower())
    return res

def load_categories():
    category_map = {}
    text_patterns = {}
    emoji_groups = {}
    for cat in AlertCategory.objects.filter(enabled=True):
        category_map[cat.name] = {"id": cat.id, "name": cat.name}
        if cat.text_patterns:
            text_patterns[cat.name] = cat.text_patterns
        if cat.emoji_patterns:
            emoji_groups[cat.name] = cat.emoji_patterns
    return category_map, text_patterns, emoji_groups

def load_locations():
    location_map = {}
    for loc in Location.objects.all():
        keys = [loc.name] + loc.synonyms
        for key in keys:
            location_map[key.lower()] = {
                "id": loc.id,
                "name": loc.name,
                "point": loc.location,
            }
    return location_map

TARGET_CHATS = load_target_chats()
EXCLUDED_USERS = load_excluded_users()
CATEGORY_MAP, TEXT_PATTERNS, EMOJI_GROUPS = load_categories()
LOCATION_MAP = load_locations()

print(f"✅ Загружено категорий: {len(CATEGORY_MAP)}")
print(f"✅ Чатов для парсинга: {len(TARGET_CHATS)}")

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF]+",
    flags=re.UNICODE
)

def extract_emojis(text: str) -> List[str]:
    return EMOJI_RE.findall(text or "")

def classify_message(text: str, emojis: List[str]) -> Optional[str]:
    if not text or len(text) > 150:
        return None

    if re.search(r"[?]|(\bкак\b)|(\bподскажите\b)", text, re.IGNORECASE):
        return None

    for category, patterns in TEXT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return category

    for category, allowed in EMOJI_GROUPS.items():
        for e in allowed:
            if e in text or any(e in emo for emo in emojis):
                return category

    return None

def get_chat_key(event) -> str:
    peer = event.message.peer_id
    if hasattr(peer, "channel_id"):
        return f"channel_{peer.channel_id}"
    if hasattr(peer, "chat_id"):
        return f"chat_{peer.chat_id}"
    if hasattr(peer, "user_id"):
        return f"user_{peer.user_id}"
    return "unknown"

async def extract_full_text(event, client) -> str:
    text = (event.raw_text or "").strip()
    if text:
        return text

    if getattr(event.message, "voice", None):
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                await client.download_media(event.message, tmp.name)
                tmp_path = tmp.name
            sber_bot = "smartspeech_sber_bot"
            sent_msg = await client.send_file(sber_bot, tmp_path)

            recognized = ""
            while True:
                await asyncio.sleep(1)
                msgs = await client.get_messages(sber_bot, limit=5)
                for msg in msgs:
                    if getattr(msg, "reply_to_msg_id", None) == sent_msg.id:
                        recognized = (msg.text or "").strip()
                        break
                if recognized:
                    break
            os.remove(tmp_path)
            return recognized
        except Exception as e:
            print(f"⚠️ Ошибка SberBot: {e}")
            return ""

    if getattr(event.message, "video_note", None) or (
        getattr(event.message, "media", None) and getattr(event.message.media, "document", None)
        and getattr(event.message.media.document, "mime_type", "").startswith("video")
    ):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                await client.download_media(event.message, tmp.name)
                video_path = tmp.name
            video_bot = "videotovoicemessage_bot"
            sent_video = await client.send_file(video_bot, video_path)

            voice_msg = None
            timeout = 30
            start_ts = time.time()
            while time.time() - start_ts < timeout:
                await asyncio.sleep(1)
                messages = await client.get_messages(video_bot, limit=10)
                for msg in messages:
                    if getattr(msg, "date", None) > event.message.date and getattr(msg, "voice", None):
                        voice_msg = msg
                        break
                if voice_msg:
                    break

            os.remove(video_path)
            if not voice_msg:
                return ""

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_voice:
                await client.download_media(voice_msg, tmp_voice.name)
                voice_path = tmp_voice.name
            sber_bot = "smartspeech_sber_bot"
            sent_msg = await client.send_file(sber_bot, voice_path)

            recognized = ""
            start_ts = time.time()
            while time.time() - start_ts < timeout:
                await asyncio.sleep(1)
                messages = await client.get_messages(sber_bot, limit=10)
                for msg in messages:
                    if getattr(msg, "reply_to_msg_id", None) == sent_msg.id:
                        recognized = (msg.text or "").strip()
                        break
                if recognized:
                    break
            os.remove(voice_path)
            return recognized
        except Exception as e:
            print(f"⚠️ Ошибка video_note: {e}")
            return ""
    return ""

async def extract_question_text(event, client) -> str:
    if not event.is_reply:
        return ""
    try:
        replied = await event.get_reply_message()
        if not replied:
            return ""
        qtext = (replied.raw_text or "").strip()
        if not qtext and (replied.voice or replied.video_note):
            try:
                t = await client(functions.messages.TranscribeAudioRequest(
                    peer=replied.peer_id,
                    msg_id=replied.id
                ))
                qtext = getattr(t, "text", "")
            except Exception:
                qtext = ""
        return qtext.strip()
    except Exception:
        return ""

def buffer_unclassified(chat_key, sender_id, text, message_id):
    ts = time.time()
    recent_unclassified_by_chat.setdefault(chat_key, []).append({
        "sender_id": sender_id,
        "text": text,
        "timestamp": ts,
        "message_id": message_id
    })

def pull_recent_unclassified(chat_key, sender_id) -> str:
    buf = recent_unclassified_by_chat.get(chat_key, [])
    now_ts = time.time()
    pulled_text = ""
    for item in reversed(buf):
        if item["sender_id"] == sender_id and (now_ts - item["timestamp"]) <= GEO_TTL_SECONDS:
            pulled_text = item.get("text", "")
            buf.remove(item)
            break
    if not buf:
        recent_unclassified_by_chat.pop(chat_key, None)
    else:
        recent_unclassified_by_chat[chat_key] = buf
    return pulled_text

def maybe_merge_with_previous(chat_key, sender_id, combined_text, category, author, payload) -> bool:
    prev_saved = last_classified_by_author.get((chat_key, sender_id))
    if prev_saved:
        prev_payload = prev_saved.get("payload")
        prev_cat = prev_payload.get("category_name")
        if not prev_cat:
            prev_payload["text"] += " " + combined_text
            prev_payload["category_name"] = category
            prev_payload["category_id"] = CATEGORY_MAP.get(category, {}).get("id")
            send_parsed_message(prev_payload)
            last_classified_by_author[(chat_key, sender_id)] = {
                "payload": prev_payload,
                "text": prev_payload["text"],
                "category": category,
                "timestamp": time.time()
            }
            print(f"↩️ Объединено с предыдущим сообщением автора {author}")
            return True
    return False

# ─────────────────────────────────────────────────────────────
# Telegram client
# ─────────────────────────────────────────────────────────────
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=TARGET_CHATS))
async def handler(event):
    sender = await event.get_sender()
    sender_id = getattr(sender, "id", None)
    username = (getattr(sender, "username", "") or "").lower()
    author = getattr(sender, "first_name", "") or getattr(sender, "username", "") or "Unknown"

    if sender_id in EXCLUDED_USERS or username in EXCLUDED_USERS:
        return

    chat_key = get_chat_key(event)

    # ── Telegram geo ─────────────────────────────
    if getattr(event.message, "geo", None):
        last_location_by_user[sender_id] = {
            "lat": event.message.geo.lat,
            "lon": event.message.geo.long,
            "ts": time.time()
        }
        return

    text = await extract_full_text(event, client)
    if not text:
        buffer_unclassified(chat_key, sender_id, "", event.message.id)
        return

    question_text = await extract_question_text(event, client)
    emojis = extract_emojis(text)
    category_name = classify_message(text, emojis)
    if not category_name:
        buffer_unclassified(chat_key, sender_id, text, event.message.id)
        return

    pulled_text = pull_recent_unclassified(chat_key, sender_id)
    combined_text = f"{pulled_text} {text}".strip() if pulled_text else text
    if question_text:
        combined_text = f"Вопрос: {question_text} | Ответ: {combined_text}"

    geo_point = last_location_by_user.pop(sender_id, None)
    matched_places = match_location(combined_text)

    payload = {
        "telegram_message_id": event.message.id,
        "chat_id": chat_key,
        "chat_title": getattr(event.chat, "title", "") if event.chat else "",
        "author_id": sender_id,
        "author_name": author,
        "text": combined_text,
        "category_id": CATEGORY_MAP.get(category_name, {}).get("id"),
        "category_name": category_name,
        "created_at": event.message.date.isoformat(),
        "locations": [],
    }

    # Telegram geo
    if geo_point:
        payload["locations"].append({
            "place_name": "telegram_location",
            "location": {"type": "Point", "coordinates": [geo_point["lon"], geo_point["lat"]]},
            "source": "telegram",
            "confidence": 1.0
        })

    # NLP geo
    for place_name, lat, lon in matched_places:
        place_info = LOCATION_MAP.get(place_name.lower())
        place_id = place_info["id"] if place_info else None
        payload["locations"].append({
            "place_name": place_name,
            "place_id": place_id,
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "source": "nlp",
            "confidence": 0.9
        })

    if maybe_merge_with_previous(chat_key, sender_id, combined_text, category_name, author, payload):
        return

    send_parsed_message(payload)
    last_classified_by_author[(chat_key, sender_id)] = {
        "payload": payload,
        "text": combined_text,
        "category": category_name,
        "timestamp": time.time()
    }

# ─────────────────────────────────────────────────────────────
# QR Login + run
# ─────────────────────────────────────────────────────────────
async def qr_login():
    await client.connect()
    if await client.is_user_authorized():
        return

    token = await client(functions.auth.ExportLoginTokenRequest(
        api_id=API_ID,
        api_hash=API_HASH,
        except_ids=[]
    ))
    tg_url = "tg://login?token=" + base64.urlsafe_b64encode(token.token).decode()
    print("📱 Сканируй QR:", tg_url)
    input("Нажми Enter после подтверждения...")

    try:
        await client.sign_in(password=input("2FA пароль (если есть): "))
    except SessionPasswordNeededError:
        pass

async def ws_listener():
    uri = "ws://localhost:8000/ws/chat-updates/"
    async for websocket in websockets.connect(uri):
        async for message in websocket:
            data = json.loads(message)
            if data.get("message") == "reload_chats":
                global TARGET_CHATS
                TARGET_CHATS = load_target_chats()
                print(f"🔄 TARGET_CHATS обновлён: {TARGET_CHATS}")
                
async def main():
    await qr_login()
    print("📡 Парсер запущен")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
