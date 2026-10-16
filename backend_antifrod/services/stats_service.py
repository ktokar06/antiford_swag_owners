from sqlalchemy import text
from sqlalchemy.orm import Session

from core.models.stats import StatsCounter

REBUILD_DAILY = """
INSERT INTO stats_daily (day, call_count, blocked, review, allow, updated_at)
SELECT c.started_at::date,
       count(*),
       count(*) FILTER (WHERE d.decision = 'auto_blocked'),
       count(*) FILTER (WHERE d.decision = 'review'),
       count(*) FILTER (WHERE d.decision = 'allow' OR d.decision IS NULL),
       now()
FROM call_record c
LEFT JOIN call_decision d ON d.call_id = c.id
WHERE c.is_valid
GROUP BY 1
"""

COUNTERS = {
    "calls_total": "SELECT count(*) FROM call_record WHERE is_valid",
    "calls_auto_blocked": "SELECT count(*) FROM call_decision WHERE decision = 'auto_blocked'",
    "calls_review": "SELECT count(*) FROM call_decision WHERE decision = 'review'",
    "calls_allow": "SELECT count(*) FROM call_decision WHERE decision = 'allow'",
    "cdr_files": "SELECT count(*) FROM cdr_file",
    "cdr_rows_invalid": "SELECT count(*) FROM invalid_cdr_row",
    "cdr_rows_duplicate": "SELECT COALESCE(SUM(rows_duplicate), 0) FROM cdr_file",
}


def get_counter(db: Session, key: str, default: int = 0) -> int:
    row = db.get(StatsCounter, key)
    return int(row.value) if row else default


def refresh_all(db: Session) -> dict:
    db.execute(text("DELETE FROM stats_daily"))
    days = db.execute(text(REBUILD_DAILY)).rowcount
    values = {k: int(db.scalar(text(sql)) or 0) for k, sql in COUNTERS.items()}
    for k, v in values.items():
        db.execute(
            text("INSERT INTO stats_counter (key, value, updated_at) VALUES (:k, :v, now()) "
                 "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"),
            {"k": k, "v": v},
        )
    return {"days": days, **values}
