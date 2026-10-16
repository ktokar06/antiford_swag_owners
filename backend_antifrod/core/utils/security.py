import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Пароль длиннее 72 байт")
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Токены сброса пароля храним в БД только в виде SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
        "type": ACCESS_TOKEN_TYPE,
    }
    if extra:
        payload.update({k: v for k, v in extra.items() if k not in payload})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require_exp": True, "require_sub": True, "require_iat": True},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise JWTError("Unexpected token type")
    return payload


__all__ = [
    "hash_password",
    "verify_password",
    "hash_token",
    "create_access_token",
    "decode_token",
    "JWTError",
]
