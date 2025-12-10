# adminparcing/management/commands/init_data.py
from django.core.management.base import BaseCommand
from adminparcing.models import EmojiGroup, TextPattern, ExcludedUser, Chat, Setting
from dotenv import load_dotenv
import os


class Command(BaseCommand):
    help = 'Инициализация данных для Telegram парсера из .env'

    def handle(self, *args, **options):
        # Загружаем .env перед os.getenv()
        load_dotenv()

        # ------------------ EmojiGroup ------------------
        emoji_groups_data = {
            "Clear": ["✅", "✔️", "☑️", "👍", "👌", "🤟", "🤘", "🤙"],
            "DPS": ["🚔", "🚓", "🚨", "👮", "👮‍♀️", "👮‍♂️"],
            "Crash": ["⚠️", "❗"],
            "Camera": ["📷", "📸", "📹", "🎥", "📽️", "🎦"]
        }
        for category, emojis in emoji_groups_data.items():
            EmojiGroup.objects.update_or_create(category=category, defaults={"emojis": emojis})

        # ------------------ TextPattern ------------------
        text_patterns_data = {
            "Clear": [r"\bчисто\b", r"\bпусто\b"],
            "DPS": [
                r"\bстоят\b", r"\bактив\b", r"\bработают\b", r"\bдпс\b", r"\bэкипаж\b",
                r"\bэкипажа\b", r"\bбратья\b", r"\bменты\b", r"\bмент\b",
                r"\bмусор\b", r"\bмусора\b", r"\bшкода\b", r"\bборт\b",
                r"\bствол\b", r"\bствола\b", r"\bпалки\b"
            ],
            "Crash": [r"\bавария\b", r"\bДТП\b"],
            "Camera": [r"\bтринога\b", r"\bкамера\b"]
        }
        for category, patterns in text_patterns_data.items():
            for pat in patterns:
                TextPattern.objects.update_or_create(category=category, pattern=pat)

        # ------------------ ExcludedUser ------------------
        excluded_users = os.getenv("EXCLUDED_USERS", "").split(",")
        for user in excluded_users:
            user = user.strip()
            if user:
                ExcludedUser.objects.update_or_create(value=user)

        # ------------------ Chat ------------------
        target_chats = os.getenv("TARGET_CHATS", "").split(",")
        for chat_id in target_chats:
            chat_id = chat_id.strip()
            if chat_id:
                Chat.objects.update_or_create(
                    chat_id=chat_id,
                    defaults={"title": chat_id, "enabled": True}
                )

        # ------------------ Settings ------------------
        settings_data = {
            "LOCAL_OFFSET": os.getenv("LOCAL_OFFSET", "0"),
            "UNCLASSIFIED_BUFFER_SECONDS": os.getenv("UNCLASSIFIED_BUFFER_SECONDS", "300"),
        }
        for key, value in settings_data.items():
            Setting.objects.update_or_create(key=key, defaults={"value": value})

        self.stdout.write(self.style.SUCCESS("✅ Данные успешно инициализированы из .env"))