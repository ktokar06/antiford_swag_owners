import base64
import json
from typing import Any

MAX_OFFSET = 1_000_000


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_offset(cursor: str | None, offset: int | None) -> int:
    """Курсор хранит смещение — корректно для любой сортировки (в отличие от last_id)."""
    if cursor:
        value = decode_cursor(cursor).get("offset", 0)
    else:
        value = offset or 0
    try:
        return max(0, min(int(value), MAX_OFFSET))
    except (TypeError, ValueError):
        return 0


def page(rows: list, limit: int, offset: int) -> tuple[list, str | None, bool]:
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor({"offset": offset + limit}) if has_more else None
    return rows, next_cursor, has_more


def digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())[:15]
