from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.SECRET_KEY_ENCRYPTION.encode())

def encrypt(value: str) -> str:
    if not value:
        return ""
    return fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if not value:
        return ""
    return fernet.decrypt(value.encode()).decode()
