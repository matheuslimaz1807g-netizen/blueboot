from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.FERNET_KEY.encode())


# ── Password ──────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Token inválido ou expirado")


# ── Fernet encryption ─────────────────────────────────────────

def encrypt_field(value: str) -> str:
    """Encrypt a sensitive string field (credentials, tokens)."""
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """Decrypt a Fernet-encrypted field."""
    if not value:
        return ""
    return _fernet.decrypt(value.encode()).decode()
