import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adminParcingPanel.settings")
django.setup()

# Теперь можно импортировать модели
from adminparcing.models import EmojiGroup, TextPattern, ExcludedUser, Chat
