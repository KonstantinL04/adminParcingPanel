from models import ExcludedUser, Chat

def load_config():
    
    excluded_users = [u.value for u in ExcludedUser.objects.all()]
    target_chats = [c.chat_id for c in Chat.objects.filter(enabled=True)]
    return excluded_users, target_chats