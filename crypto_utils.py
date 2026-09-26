import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

_key = os.getenv("ENCRYPTION_KEY")
if not _key:
    raise RuntimeError(
        "Не задан ENCRYPTION_KEY. Выполните python generate_key.py "
        "и добавьте полученный ключ в .env: ENCRYPTION_KEY=ваш_ключ."
    )

try:
    _cipher = Fernet(_key.encode("ascii"))
except (ValueError, TypeError, UnicodeError):
    raise RuntimeError(
        "Некорректный ENCRYPTION_KEY: требуется действительный ключ Fernet."
    ) from None


def encrypt_value(value: str) -> str:
    return _cipher.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(token: str) -> str:
    try:
        return _cipher.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, AttributeError, TypeError):
        raise ValueError(
            "Не удалось расшифровать значение: проверьте ENCRYPTION_KEY "
            "и целостность данных. Незашифрованные записи требуют миграции."
        ) from None
