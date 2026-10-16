from collections.abc import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.models.user import AppUser
from core.utils.security import JWTError, decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_db_dep() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db_dep),
) -> AppUser:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise _unauthorized("Invalid token")
    user = db.get(AppUser, user_id)
    if not user or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user
