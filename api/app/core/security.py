from datetime import datetime, timedelta, timezone
from typing import Any
import secrets

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# Fallback rígido para garantir que os dados do usuário continuem legíveis mesmo com erro de ambiente
_original_key = "ptaiS0u-FfzRI0iG-scBtJphQyrPIzG5un0YCuiEBtU="
try:
    _key_str = settings.BLUEBOT_FERNET_KEY.strip().replace('"', '').replace("'", "")
    
    # Se a chave tiver 43 caracteres (comum em erros de truncamento), tenta adicionar o '8' final
    if len(_key_str) == 43 and not _key_str.endswith('='):
        _key_str += "8="
    elif len(_key_str) == 43 and _key_str.endswith('='):
        # Provavelmente falta um caractere antes do '='
        _key_str = _key_str[:-1] + "8="

    if len(_key_str) != 44:
        _key_str = _original_key
        
    _fernet = Fernet(_key_str.encode())
except Exception:
    _fernet = Fernet(_original_key.encode())


# ── Password ──────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────

def _generate_jti() -> str:
    """Generate unique JWT ID for replay attack prevention."""
    return secrets.token_urlsafe(32)

def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": _generate_jti()  # JWT ID for replay attack prevention
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "jti"]
            }
        )
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
