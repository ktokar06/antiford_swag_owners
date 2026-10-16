"""
Признаки номеров за окно времени — считаются одним set-based SQL по call_record:
  phone_number   — все номера из CDR (A, B, C), регион/оператор по префиксу, first/last seen
  subscriber     — абоненты по IMSI, phone_number.subscriber_id — самый частый IMSI номера
  number_feature — вызовов в час (пик), собеседники, охват регионов, доли коротких и неотвеченных

Запуск: python -m etl.load_features
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from core import telecom
from core.database import SessionLocal

SHORT_CALL_SEC = 10


def _in_list(codes) -> str:
    return ", ".join(f"'{c}'" for c in sorted(codes))


UPSERT_PHONES = f"""
INSERT INTO phone_number (number, region_code, operator_code, kind, is_valid, first_seen, last_seen)
SELECT n.number, substr(n.number, 1, 3), substr(n.number, 1, 3),
       CASE WHEN substr(n.number, 1, 3) IN ({_in_list(telecom.CITY_CODES)}) THEN 'landline'
            WHEN substr(n.number, 1, 3) IN ({_in_list(telecom.MOBILE_CODES)}) THEN 'mobile'
            ELSE 'unknown' END,
       TRUE, MIN(n.started_at), MAX(n.started_at)
FROM (
    SELECT caller_number AS number, started_at FROM call_record WHERE is_valid
    UNION ALL
    SELECT callee_number, started_at FROM call_record WHERE is_valid
    UNION ALL
    SELECT forward_number, started_at FROM call_record WHERE is_valid AND forward_number IS NOT NULL
) n
GROUP BY n.number
ON CONFLICT (number) DO UPDATE SET
    region_code = EXCLUDED.region_code,
    operator_code = EXCLUDED.operator_code,
    kind = EXCLUDED.kind,
    first_seen = EXCLUDED.first_seen,
    last_seen = EXCLUDED.last_seen
"""

UPSERT_SUBSCRIBERS = """
INSERT INTO subscriber (external_id, kind)
SELECT DISTINCT imsi, 'person' FROM call_record WHERE is_valid AND imsi IS NOT NULL
ON CONFLICT (external_id) DO NOTHING
"""

LINK_SUBSCRIBERS = """
UPDATE phone_number pn SET subscriber_id = s.id
FROM (
    SELECT DISTINCT ON (caller_number) caller_number, imsi
    FROM call_record
    WHERE is_valid AND imsi IS NOT NULL
    GROUP BY caller_number, imsi
    ORDER BY caller_number, count(*) DESC, imsi
) m
JOIN subscriber s ON s.external_id = m.imsi
WHERE pn.number = m.caller_number AND pn.subscriber_id IS DISTINCT FROM s.id
"""

WINDOW_DAYS = """
SELECT COALESCE(MAX(started_at)::date - MIN(started_at)::date + 1, 0) FROM call_record WHERE is_valid
"""

UPSERT_FEATURES = f"""
WITH outg AS (
    SELECT caller_number AS number,
           count(*) AS calls,
           count(DISTINCT substr(callee_number, 1, 3)) AS regions,
           count(*) FILTER (WHERE duration_sec <= {SHORT_CALL_SEC}) AS short_calls,
           count(*) FILTER (WHERE duration_sec = 0) AS zero_calls
    FROM call_record WHERE is_valid
    GROUP BY caller_number
), hourly AS (
    SELECT number, MAX(cnt) AS peak FROM (
        SELECT caller_number AS number, date_trunc('hour', started_at) AS h, count(*) AS cnt
        FROM call_record WHERE is_valid
        GROUP BY 1, 2
    ) x GROUP BY number
), inc AS (
    SELECT callee_number AS number, count(*) AS calls
    FROM call_record WHERE is_valid
    GROUP BY callee_number
), fwd AS (
    SELECT caller_number AS number FROM call_record WHERE is_valid AND forward_number IS NOT NULL
    UNION
    SELECT forward_number FROM call_record WHERE is_valid AND forward_number IS NOT NULL
), cp AS (
    SELECT number, count(DISTINCT other) AS cnt FROM (
        SELECT caller_number AS number, callee_number AS other FROM call_record WHERE is_valid
        UNION ALL
        SELECT callee_number, caller_number FROM call_record WHERE is_valid
    ) p GROUP BY number
), nps AS (
    SELECT subscriber_id, count(*) AS cnt
    FROM phone_number WHERE subscriber_id IS NOT NULL
    GROUP BY subscriber_id
)
INSERT INTO number_feature (
    phone_number_id, window_days, total_calls, outgoing_calls, calls_per_hour,
    unique_counterparts, region_reach, short_call_share, unanswered_share,
    has_incoming, has_outgoing, has_forwarded, numbers_per_subscriber, computed_at
)
SELECT pn.id, :window_days,
       COALESCE(o.calls, 0) + COALESCE(i.calls, 0),
       COALESCE(o.calls, 0),
       COALESCE(h.peak, 0),
       COALESCE(cp.cnt, 0),
       COALESCE(o.regions, 0),
       CASE WHEN o.calls > 0 THEN round(o.short_calls::numeric / o.calls, 4) ELSE 0 END,
       CASE WHEN o.calls > 0 THEN round(o.zero_calls::numeric / o.calls, 4) ELSE 0 END,
       i.number IS NOT NULL,
       o.number IS NOT NULL,
       f.number IS NOT NULL,
       COALESCE(nps.cnt, 1),
       now()
FROM phone_number pn
LEFT JOIN outg o ON o.number = pn.number
LEFT JOIN hourly h ON h.number = pn.number
LEFT JOIN inc i ON i.number = pn.number
LEFT JOIN fwd f ON f.number = pn.number
LEFT JOIN cp ON cp.number = pn.number
LEFT JOIN nps ON nps.subscriber_id = pn.subscriber_id
ON CONFLICT (phone_number_id) DO UPDATE SET
    window_days = EXCLUDED.window_days,
    total_calls = EXCLUDED.total_calls,
    outgoing_calls = EXCLUDED.outgoing_calls,
    calls_per_hour = EXCLUDED.calls_per_hour,
    unique_counterparts = EXCLUDED.unique_counterparts,
    region_reach = EXCLUDED.region_reach,
    short_call_share = EXCLUDED.short_call_share,
    unanswered_share = EXCLUDED.unanswered_share,
    has_incoming = EXCLUDED.has_incoming,
    has_outgoing = EXCLUDED.has_outgoing,
    has_forwarded = EXCLUDED.has_forwarded,
    numbers_per_subscriber = EXCLUDED.numbers_per_subscriber,
    computed_at = EXCLUDED.computed_at
"""


def compute_number_features(db: Session) -> dict:
    phones = db.execute(text(UPSERT_PHONES)).rowcount
    db.execute(text(UPSERT_SUBSCRIBERS))
    db.execute(text(LINK_SUBSCRIBERS))
    window_days = int(db.scalar(text(WINDOW_DAYS)) or 0)
    features = db.execute(text(UPSERT_FEATURES), {"window_days": window_days}).rowcount
    return {"phone_numbers": phones, "number_features": features, "window_days": window_days}


def main():
    db = SessionLocal()
    try:
        print(compute_number_features(db))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
