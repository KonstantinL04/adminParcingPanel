from models import EmojiGroup, TextPattern, ExcludedUser, Chat

def load_config():
    emoji_groups = {e.category: e.emojis for e in EmojiGroup.objects.all()}
    text_patterns = {}
    for t in TextPattern.objects.all():
        text_patterns.setdefault(t.category, []).append(t.pattern)
    excluded_users = [u.value for u in ExcludedUser.objects.all()]
    target_chats = [c.chat_id for c in Chat.objects.filter(enabled=True)]
    return emoji_groups, text_patterns, excluded_users, target_chats