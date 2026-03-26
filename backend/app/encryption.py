from cryptography.fernet import Fernet

from app.config import settings

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            key = Fernet.generate_key().decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_api_key(api_key: str) -> str:
    return _get_fernet().encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "***"
    return api_key[:3] + "*" * (len(api_key) - 7) + api_key[-4:]
