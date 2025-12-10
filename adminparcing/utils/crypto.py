from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    key = settings.SECRET_KEY_ENCRYPTION
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)

fernet = get_fernet()