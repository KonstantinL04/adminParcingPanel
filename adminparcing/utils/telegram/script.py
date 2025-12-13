#!/usr/bin/env python3
# main_telethon_qr.py

import os
import re
import base64
import qrcode
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any
from openpyxl import Workbook, load_workbook
from telethon import TelegramClient, events, functions
from telethon.errors import SessionPasswordNeededError
from telethon.tl import types
from dotenv import load_dotenv
import tempfile
import time
from adminparcing.utils.nlp.NLPModel import match_location
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")  
django.setup()

from adminparcing.models import (
    Chat,
    AlertCategory,
    ExcludedUser,
    SettingAPI,
)

# ===================== НАСТРОЙКИ =====================
load_dotenv()
def load_api_credentials():
    api_id = SettingAPI.objects.get(key="API_ID").value
    api_hash = SettingAPI.objects.get(key="API_HASH").value
    session_name = SettingAPI.objects.get(key="SESSION_NAME").value
    return int(api_id), api_hash, session_name

API_ID, API_HASH, SESSION_NAME = load_api_credentials()
EXCEL_FILE = "new_messages.xlsx"

# -------------------- БУФФЕРЫ --------------------
last_saved_by_chat: Dict[Any, Dict[str, Any]] = {}
recent_unclassified_by_chat: Dict[Any, List[Dict[str, Any]]] = {}
last_location_by_user: Dict[int, Dict[str, Any]] = {}
last_classified_by_author: Dict[Tuple[str, int], Dict[str, Any]] = {}

# ============= ЧАТЫ ДЛЯ МОНИТОРИНГА ==============
def load_target_chats():
    chats = []
    for c in Chat.objects.filter(enabled=True):
        try:
            chats.append(int(c.chat_id))
        except ValueError:
            chats.append(c.chat_id)
    return chats

TARGET_CHATS = load_target_chats()

print(TARGET_CHATS)
# ============= БЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ ==============
def load_excluded_users():
    result = []
    for u in ExcludedUser.objects.all():
        if u.value.isdigit():
            result.append(int(u.value))
        else:
            result.append(u.value.lower())
    return result

EXCLUDED_USERS = load_excluded_users()
   
# ===================== ЛОКАЛЬНОЕ ВРЕМЯ =====================         
LOCAL_OFFSET_ENV = os.getenv("LOCAL_OFFSET", "")
if LOCAL_OFFSET_ENV != "":
    try:
        LOCAL_OFFSET = int(LOCAL_OFFSET_ENV)
        LOCAL_TZ = timezone(timedelta(hours=LOCAL_OFFSET))
    except Exception:
        LOCAL_TZ = datetime.now().astimezone().tzinfo
else:
    LOCAL_TZ = datetime.now().astimezone().tzinfo
    
# ---- настройка буфера сверху в файле (глобально) ----
UNCLASSIFIED_BUFFER_SECONDS = int(os.getenv("UNCLASSIFIED_BUFFER_SECONDS", "300"))  # 5 минут по умолчанию

# ===================== КЛАССИФИКАЦИЯ =====================
def load_categories():
    emoji_groups = {}
    text_patterns = {}

    for cat in AlertCategory.objects.filter(enabled=True):
        if cat.emoji_patterns:
            emoji_groups[cat.name] = cat.emoji_patterns
        if cat.text_patterns:
            text_patterns[cat.name] = cat.text_patterns

    return emoji_groups, text_patterns


emoji_groups, text_patterns = load_categories()

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def safe_sheet_title(name: str) -> str:
    return re.sub(r'[\\/*?:\[\]]', "_", name)[:31]

def extract_emojis(text: str) -> List[str]:
    emoji_pattern = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
                               "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+", flags=re.UNICODE)
    return emoji_pattern.findall(text or "")

def classify_message(text: str, emojis: List[str]) -> Tuple[Optional[str], str]:
    if not text:
        return None, text

    if re.search(r"[?]|(\bкак\b)|(\bподскажите\b)", text, re.IGNORECASE):
        return None, text
    if len(text) > 100:
        return None, text

    for category, patterns in text_patterns.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                if category == "Clear" and "✅" not in text:
                    text += " ✅"
                elif category == "DPS" and "🚔" not in text:
                    text += " 🚔"
                elif category == "Crash" and "⚠️" not in text:
                    text += " ⚠️"
                elif category == "Camera" and "📸" not in text:
                    text += " 📸"
                return category, text

    for category, allowed in emoji_groups.items():
        for e in allowed:
            if e in text or any(e in emo for emo in emojis):
                return category, text

    return None, text

def format_event_time(ev_date: datetime) -> str:
    try:
        utc_dt = ev_date.replace(tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(LOCAL_TZ)
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ev_date.strftime("%Y-%m-%d %H:%M:%S")

# ===================== EXCEL =====================
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws_all = wb.active
        ws_all.title = "Messages"
        ws_all.append(["Time", "Author", "Message", "Category", "Place", "lat", "lon"])

        for cat in emoji_groups.keys():
            ws = wb.create_sheet(safe_sheet_title(cat))
            ws.append(["Time", "Author", "Message", "Category", "Place", "lat", "lon"])

        wb.save(EXCEL_FILE)
    else:
        wb = load_workbook(EXCEL_FILE)
    return wb

def save_to_excel(time_str: str, author: str, text: str, category: Optional[str], place: str,
                  lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
    if not category:
        category = "Unknown"
    wb = load_workbook(EXCEL_FILE)
    ws_all = wb["Messages"]
    ws_all.append([time_str, author, text, category, place or "", lat or "", lon or ""]) 
    all_row = ws_all.max_row

    if category not in wb.sheetnames:
        ws_cat = wb.create_sheet(safe_sheet_title(category))
        ws_cat.append(["Time", "Author", "Message", "Category", "Place", "lat", "lon"])
    ws_cat = wb[safe_sheet_title(category)]
    ws_cat.append([time_str, author, text, category, place or "", lat or "", lon or ""])  
    cat_row = ws_cat.max_row

    wb.save(EXCEL_FILE)
    return {"all_row": all_row, "cat": category, "cat_row": cat_row}

def update_saved_entry(saved_info: Dict[str, Any], new_time_str: str, author: str,
                       new_text: str, new_category: str, new_place: str,
                       lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:  
    wb = load_workbook(EXCEL_FILE)
    ws_all = wb["Messages"]

    r = saved_info.get("all_row")
    if r:
        ws_all.cell(row=r, column=1, value=new_time_str)
        ws_all.cell(row=r, column=2, value=author)
        ws_all.cell(row=r, column=3, value=new_text)
        ws_all.cell(row=r, column=4, value=new_category)
        ws_all.cell(row=r, column=5, value=new_place)
        ws_all.cell(row=r, column=6, value=lat or "")
        ws_all.cell(row=r, column=7, value=lon or "")

    old_cat = saved_info.get("cat")
    old_cat_row = saved_info.get("cat_row")
    if old_cat == new_category and old_cat_row:
        ws_cat = wb[safe_sheet_title(old_cat)]
        ws_cat.cell(row=old_cat_row, column=1, value=new_time_str)
        ws_cat.cell(row=old_cat_row, column=2, value=author)
        ws_cat.cell(row=old_cat_row, column=3, value=new_text)
        ws_cat.cell(row=old_cat_row, column=4, value=new_category)
        ws_cat.cell(row=old_cat_row, column=5, value=new_place)
        ws_cat.cell(row=old_cat_row, column=6, value=lat or "")
        ws_cat.cell(row=old_cat_row, column=7, value=lon or "")
    else:
        if old_cat and old_cat_row and old_cat in wb.sheetnames:
            try:
                ws_old = wb[safe_sheet_title(old_cat)]
                ws_old.delete_rows(old_cat_row)
            except Exception:
                pass
        if new_category not in wb.sheetnames:
            ws_new = wb.create_sheet(safe_sheet_title(new_category))
            ws_new.append(["Time", "Author", "Message", "Category", "Place", "lat", "lon"])
        ws_new = wb[safe_sheet_title(new_category)]
        ws_new.append([new_time_str, author, new_text, new_category, new_place, lat or "", lon or ""])
        saved_info["cat"] = new_category
        saved_info["cat_row"] = ws_new.max_row

    wb.save(EXCEL_FILE)
    return saved_info

# ===================== TELETHON =====================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

def get_chat_key(event) -> str:
    # Create stable chat key for dictionaries
    try:
        if event.is_private:
            return f"user_{event.message.peer_id.user_id}"
    except Exception:
        pass
    peer = event.message.peer_id
    if hasattr(peer, "channel_id") and peer.channel_id:
        return f"channel_{peer.channel_id}"
    if hasattr(peer, "chat_id") and peer.chat_id:
        return f"chat_{peer.chat_id}"
    if hasattr(peer, "user_id") and peer.user_id:
        return f"user_{peer.user_id}"
    return str(getattr(event.chat_id, "value", "unknown"))

def prune_unclassified_buffer(chat_key: str):
    buf = recent_unclassified_by_chat.get(chat_key, [])
    if not buf:
        recent_unclassified_by_chat.pop(chat_key, None)
        return
    now_ts = datetime.now().timestamp()
    new_buf = [it for it in buf if (now_ts - it["timestamp"]) <= UNCLASSIFIED_BUFFER_SECONDS]
    if new_buf:
        recent_unclassified_by_chat[chat_key] = new_buf
    else:
        recent_unclassified_by_chat.pop(chat_key, None)

# -------------------- ОСНОВНЫЕ ФУНКЦИИ --------------------
# Извлекает текст сообщения
#Если это аудио/видео, пересылает боту @smartspeech_sber_bot для расшифровки.
async def extract_text(event, client):
    text = (event.raw_text or "").strip()
    
    if text:
        return text

    # ------------------ Голосовое сообщение ------------------
    if event.message.voice:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                await client.download_media(event.message, tmp.name)
                tmp_path = tmp.name

            print("🎙 Отправка голосового сообщения SberBot для расшифровки...")
            sber_bot = "smartspeech_sber_bot"
            sent_msg = await client.send_file(sber_bot, tmp_path)

            # Ждём ответа бота, который является reply на наше сообщение
            recognized = ""
            while True:
                await asyncio.sleep(1)
                messages = await client.get_messages(sber_bot, limit=5)
                for msg in messages:
                    if getattr(msg, "reply_to_msg_id", None) == sent_msg.id:
                        recognized = (msg.text or "").strip()
                        break
                if recognized:
                    break

            os.remove(tmp_path)
            return recognized

        except Exception as e:
            print(f"⚠️ Ошибка при расшифровке SberBot: {e}")
            return ""

    # ------------------ Короткое видео / video_note ------------------
    if event.message.video_note or (
        event.message.media and getattr(event.message.media, "document", None)
        and getattr(event.message.media.document, "mime_type", "").startswith("video")
    ):
        try:
            # Скачиваем видео
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
                await client.download_media(event.message, tmp_video.name)
                video_path = tmp_video.name

            print("🎬 Отправка video_note в VideoToVoiceBot...")
            video_bot = "videotovoicemessage_bot"
            sent_video = await client.send_file(video_bot, video_path)

            # Ждём первое голосовое сообщение от бота после отправки
            voice_msg = None
            timeout = 30  # секунд
            start_ts = time.time()
            while time.time() - start_ts < timeout:
                await asyncio.sleep(1)
                messages = await client.get_messages(video_bot, limit=10)
                for msg in messages:
                    # Берём первое голосовое сообщение, которое пришло после отправки
                    if getattr(msg, "date", None) > event.message.date and msg.voice:
                        voice_msg = msg
                        break
                if voice_msg:
                    break

            os.remove(video_path)
            if not voice_msg:
                print("⚠️ Не удалось получить голосовое сообщение от VideoToVoiceBot")
                return ""

            # Скачиваем голосовое сообщение и отправляем SberBot
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_voice:
                await client.download_media(voice_msg, tmp_voice.name)
                voice_path = tmp_voice.name

            sber_bot = "smartspeech_sber_bot"
            sent_msg = await client.send_file(sber_bot, voice_path)

            # Ждём расшифровку от SberBot
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
            print(f"⚠️ Ошибка при обработке video_note: {e}")
            return ""

#Получение текста вопроса (если сообщение – ответ)
async def extract_question_text(event, client):
    if not event.is_reply:
        return ""
    try:
        replied = await event.get_reply_message()
        if not replied:
            return ""
        qtext = (replied.raw_text or "").strip()

        # Транскрипция, если вопрос — аудио/видео
        if not qtext and (replied.voice or replied.video_note or (
            replied.media and getattr(replied.media, "document", None)
            and getattr(replied.media.document, "mime_type", "").startswith("audio")
        )):
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

#Работа с буфером непризнанных сообщений
def buffer_unclassified(chat_key, sender_id, text, message_id):
    ts = datetime.now().timestamp()
    recent_unclassified_by_chat.setdefault(chat_key, []).append({
        "sender_id": sender_id,
        "text": text,
        "timestamp": ts,
        "message_id": message_id
    })
    prune_unclassified_buffer(chat_key)

def pull_recent_unclassified(chat_key, sender_id):
    buf = recent_unclassified_by_chat.get(chat_key, [])
    now_ts = datetime.now().timestamp()
    pulled_text = ""
    for item in reversed(buf):
        if item["sender_id"] == sender_id and (now_ts - item["timestamp"]) <= UNCLASSIFIED_BUFFER_SECONDS:
            pulled_text = item.get("text", "")
            buf.remove(item)
            break
    if not buf:
        recent_unclassified_by_chat.pop(chat_key, None)
    else:
        recent_unclassified_by_chat[chat_key] = buf
    return pulled_text

#Обновление предыдущей записи (если она не классифицирована)
def maybe_merge_with_previous(chat_key, sender_id, combined_text, category, author, event):
    prev_saved = last_saved_by_chat.get(chat_key)
    if prev_saved and prev_saved.get("sender_id") == sender_id:
        prev_cat = prev_saved.get("saved_info", {}).get("cat")
        if not prev_cat or prev_cat == "None":
            new_text = (prev_saved.get("text", "") + " " + combined_text).strip()
            emojis_comb = extract_emojis(new_text)
            new_cat, new_processed = classify_message(new_text, emojis_comb)
            if not new_cat:
                new_cat, new_processed = category, new_text
            time_str = format_event_time(event.message.date)
            saved_info = prev_saved.get("saved_info")
            updated_info = update_saved_entry(saved_info, time_str, author, new_processed, new_cat)
            last_saved_by_chat[chat_key] = {
                "sender_id": sender_id,
                "saved_info": updated_info,
                "text": new_processed
            }
            print("↩️ Обновлена предыдущая запись (объединение непризнанного с классифицированным):")
            print(f"🕒 {time_str} | {author} | {new_processed} | {new_cat}")
            return True
    return False

# -------------------- Main message handler --------------------
@client.on(events.NewMessage(chats=TARGET_CHATS))
async def handler(event):
    sender = await event.get_sender()
    sender_id = getattr(sender, "id", None)
    username = (getattr(sender, "username", "") or "").lower()
    author = getattr(sender, "first_name", "") or getattr(sender, "username", "") or "Unknown"

    if sender_id in EXCLUDED_USERS or (username and username in EXCLUDED_USERS):
        print(f"🚫 Игнорируем сообщение от {username or sender_id}")
        return

    chat_key = get_chat_key(event)

    # ---------- Проверка: геометка ----------
    if getattr(event.message, "geo", None):
        lat = event.message.geo.lat
        lon = event.message.geo.long
        time_str = format_event_time(event.message.date)
        key = (chat_key, sender_id)

        # 🧭 Геометка после классификации — обновляем Excel
        if key in last_classified_by_author:
            info = last_classified_by_author[key]
            saved_info = info["saved_info"]
            wb = load_workbook(EXCEL_FILE)
            ws_all = wb["Messages"]
            r = saved_info["all_row"]

            ws_all.cell(row=r, column=5, value=lat)
            ws_all.cell(row=r, column=6, value=lon)

            cat = saved_info["cat"]
            if cat in wb.sheetnames:
                ws_cat = wb[safe_sheet_title(cat)]
                ws_cat.cell(row=saved_info["cat_row"], column=5, value=lat)
                ws_cat.cell(row=saved_info["cat_row"], column=6, value=lon)
            wb.save(EXCEL_FILE)

            print(f"📍 Добавлены координаты к последнему сообщению автора {author}: {lat}, {lon}")
            del last_classified_by_author[key]
        else:
            # 🗺 Геометка до классификации — запоминаем
            last_location_by_user[sender_id] = {
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().timestamp()
            }
            print(f"📍 Геометка сохранена: {lat}, {lon}")
        return

    # ---------- Получаем текст (в том числе аудио/видео) ----------
    text = await extract_text(event, client)
    if not text:
        buffer_unclassified(chat_key, sender_id, "", event.message.id)
        return

    # ---------- Проверка на вопрос ----------
    question_text = await extract_question_text(event, client)
    emojis = extract_emojis(text)
    category, processed_text = classify_message(text, emojis)

    if not category:
        buffer_unclassified(chat_key, sender_id, text, event.message.id)
        return

    pulled_text = pull_recent_unclassified(chat_key, sender_id)
    combined_text = f"{pulled_text} {processed_text}".strip() if pulled_text else processed_text
    if question_text:
        combined_text = f"Вопрос: {question_text} | Ответ: {combined_text}"

    # ---------- Геометка до классификации ----------
    location = last_location_by_user.get(sender_id)
    lat = lon = None
    if location and (datetime.now().timestamp() - location["timestamp"] <= 300):
        lat, lon = location["lat"], location["lon"]
        del last_location_by_user[sender_id]

    # ---------- Автоопределение мест (NLP) ----------
    matched_places = match_location(combined_text)
    print(f"🔍 NLP анализ: '{combined_text}'")
    print(f"📋 Найдено мест: {len(matched_places)}")
    for i, (place, lat, lon) in enumerate(matched_places):
        print(f"  {i+1}. '{place}' -> {lat}, {lon}")
    
    # ---------- Если найдено несколько мест ----------
    if len(matched_places) > 1:
        print(f"🔍 Найдено {len(matched_places)} мест в сообщении:")
        
        # Для нескольких мест создаем отдельную запись для каждого
        for i, (place_name, nlp_lat, nlp_lon) in enumerate(matched_places):
            # Используем координаты из NLP для каждого места
            current_lat, current_lon = nlp_lat, nlp_lon
            
            # ---------- Сохраняем в Excel ----------
            time_str = format_event_time(event.message.date)
            # Для каждого места создаем отдельную запись с его координатами
            saved_info = save_to_excel(time_str, author, combined_text, category, place_name, current_lat, current_lon)

            # ---------- Лог в консоль ----------
            print(f"📍 Место {i+1}: {place_name}")
            print(f"📍 Координаты: {current_lat}, {current_lon}")
                
        print("───────────────────────────────\n")
        return

    # ---------- Если найдено одно или ноль мест (старая логика) ----------
    place = ""
    current_lat, current_lon = lat, lon
    
    if matched_places:
        place, nlp_lat, nlp_lon = matched_places[0]
        if not current_lat or not current_lon:
            current_lat, current_lon = nlp_lat, nlp_lon

    # ---------- Проверяем слияние с предыдущим ----------
    if maybe_merge_with_previous(chat_key, sender_id, combined_text, category, author, event):
        return

    # ---------- Сохраняем в Excel ----------
    time_str = format_event_time(event.message.date)
    saved_info = save_to_excel(time_str, author, combined_text, category, place, current_lat, current_lon)

    last_saved_by_chat[chat_key] = {
        "sender_id": sender_id,
        "saved_info": saved_info,
        "text": combined_text
    }
    last_classified_by_author[(chat_key, sender_id)] = {
        "saved_info": saved_info,
        "timestamp": datetime.now().timestamp()
    }

    # ---------- Лог в консоль ----------
    print("───────────────────────────────")
    print(f"🕒 Время: {time_str}")
    print(f"👤 Автор: {author}")
    print(f"💬 Сообщение: {combined_text}")
    print(f"📁 Категория: {category}")
    print(f"📍 Место: {place}")
    if current_lat and current_lon:
        print(f"📍 Координаты: {current_lat}, {current_lon}")
    print("───────────────────────────────\n")

# ===================== QR-КОД ЛОГИН С 2FA =====================
async def qr_login():
    await client.connect()
    if await client.is_user_authorized():
        print("✅ Уже авторизован")
        return

    try:
        login_token = await client(functions.auth.ExportLoginTokenRequest(
            api_id=API_ID,
            api_hash=API_HASH,
            except_ids=[]
        ))
        token_bytes = login_token.token
        token_b64url = base64.urlsafe_b64encode(token_bytes).decode('utf-8')
        tg_url = f"tg://login?token={token_b64url}"

        qr = qrcode.QRCode()
        qr.add_data(tg_url)
        qr.make()
        print("📱 Сканируй QR-код:\n")
        qr.print_ascii(invert=True)
        print("\nСсылка:", tg_url)

        # Ждем подтверждения QR-кода через Enter
        input("✅ После того как QR-код подтверждён на телефоне, нажми Enter для продолжения...")

        # Проверяем авторизацию
        if not await client.is_user_authorized():
            print("⏳ Подтверждение ещё не получено, попробуем авторизоваться...")
        
        # Если включена 2FA, запросим пароль
        try:
            await client.sign_in(password=input("🔑 Введи пароль двухфакторной аутентификации (если включен): "))
        except SessionPasswordNeededError:
            # Пароль не нужен
            pass

        print("✅ Авторизация завершена, сессия активна!")

    except Exception as e:
        print("❌ Ошибка при QR-логине:", e)
# ===================== ЗАПУСК =====================
async def wait_for_exit():
    await asyncio.to_thread(input, "🚪 Нажми Enter, чтобы остановить парсинг и выйти...\n")
    print("⏹ Остановка клиента...")
    await client.disconnect()

async def main():
    if API_ID == 0 or not API_HASH:
        print("❌ Укажи API_ID и API_HASH")
        return

    init_excel()
    await qr_login()

    if not await client.is_user_authorized():
        print("❌ Не авторизован")
        return

    print("📡 Парсер запущен")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
