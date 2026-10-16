import logging
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import settings
from core.models.user import AppUser, PasswordResetToken
from core.utils.security import create_access_token, hash_password, hash_token, verify_password
from services import email_service

log = logging.getLogger(__name__)

# Фиктивный хеш, чтобы время ответа не выдавало существование email
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _get_by_email(db: Session, email: str) -> AppUser | None:
    return db.execute(select(AppUser).where(AppUser.email == normalize_email(email))).scalar_one_or_none()


def login(db: Session, email: str, password: str) -> dict:
    user = _get_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Аккаунт деактивирован")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "access_token": create_access_token(str(user.id), {"role": user.role}),
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_hours * 3600,
    }


def request_password_reset(db: Session, email: str) -> dict:
    user = _get_by_email(db, email)
    if user and user.is_active:
        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_ttl_minutes)
        db.add(PasswordResetToken(user_id=user.id, token=hash_token(token), expires_at=expires))
        db.commit()
        try:
            email_service.send_reset_email(user.email, token)
        except Exception:
            log.exception("Не удалось отправить письмо сброса пароля")
    # Ответ одинаковый для существующих и несуществующих адресов
    return {"status": "ok"}


def reset_password(db: Session, token: str, new_password: str) -> dict:
    row = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise HTTPException(400, "Токен не найден или уже использован")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Срок действия токена истёк")
    user = db.get(AppUser, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(400, "Пользователь не найден")
    user.password_hash = hash_password(new_password)
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok"}


def change_password(db: Session, user: AppUser, old_password: str, new_password: str) -> dict:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(400, "Старый пароль неверный")
    user.password_hash = hash_password(new_password)
    db.commit()
    return {"status": "ok"}


def ensure_operator(db: Session) -> None:
    """Создаёт первого оператора из OPERATOR_EMAIL / OPERATOR_PASSWORD."""
    if not settings.operator_email or not settings.operator_password:
        return
    if (db.scalar(select(func.count()).select_from(AppUser)) or 0) > 0:
        return
    if len(settings.operator_password) < 8:
        log.error("OPERATOR_PASSWORD короче 8 символов — оператор не создан")
        return
    db.add(AppUser(
        email=normalize_email(settings.operator_email),
        password_hash=hash_password(settings.operator_password),
        role="operator",
        full_name="Оператор",
        is_active=True,
    ))
    db.commit()
    log.info("Создан оператор %s", normalize_email(settings.operator_email))
