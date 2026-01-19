from cryptography.fernet import Fernet
from django.conf import settings


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')


fernet = Fernet(settings.SECRET_KEY_ENCRYPTION.encode())

def encrypt(value: str) -> str:
    if not value:
        return ""
    return fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if not value:
        return ""
    return fernet.decrypt(value.encode()).decode()
