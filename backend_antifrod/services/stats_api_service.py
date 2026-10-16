"""Агрегаты для дашборда и графиков: всё считается в БД, клиенту уходят готовые ряды."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from etl.cdr_parser import ERROR_LABELS

SUMMARY_SQL = """
SELECT
    (SELECT count(*) FROM call_record WHERE is_valid)                         AS calls_total,
    (SELECT count(*) FROM call_decision WHERE decision = 'auto_blocked')      AS calls_blocked,
    (SELECT count(*) FROM call_decision WHERE decision = 'review')            AS calls_review,
    (SELECT count(*) FROM call_decision WHERE decision = 'allow')             AS calls_allow,
    (SELECT count(*) FROM call_record c WHERE NOT EXISTS
        (SELECT 1 FROM call_decision d WHERE d.call_id = c.id))               AS calls_unscored,
    (SELECT count(*) FROM invalid_cdr_row)                                    AS rows_invalid,
    (SELECT COALESCE(SUM(rows_duplicate), 0) FROM cdr_file)                   AS rows_duplicate,
    (SELECT COALESCE(SUM(rows_total), 0) FROM cdr_file)                       AS rows_total,
    (SELECT count(*) FROM cdr_file)                                           AS files,
    (SELECT count(*) FROM phone_number)                                       AS numbers_total,
    (SELECT count(*) FROM number_feature WHERE has_fan_pattern)               AS numbers_in_fans,
    (SELECT count(DISTINCT c.caller_number) FROM call_decision d
        JOIN call_record c ON c.id = d.call_id WHERE d.decision = 'auto_blocked') AS numbers_blocked,
    (SELECT count(*) FROM graph_cluster)                                      AS clusters,
    (SELECT count(*) FROM call_review WHERE status_code = 'pending')          AS reviews_pending,
    (SELECT min(started_at) FROM call_record)                                 AS period_from,
    (SELECT max(started_at) FROM call_record)                                 AS period_to,
    (SELECT round(avg(risk_score), 2) FROM call_decision)                     AS avg_risk_score
"""

DAILY_SQL = """
SELECT day, call_count, blocked, review, allow FROM stats_daily ORDER BY day
"""

HOURLY_SQL = """
SELECT EXTRACT(hour FROM c.started_at)::int AS hour,
       count(*) AS calls,
       count(*) FILTER (WHERE d.decision = 'auto_blocked') AS blocked,
       count(*) FILTER (WHERE d.decision = 'review') AS review
FROM call_record c LEFT JOIN call_decision d ON d.call_id = c.id
WHERE c.is_valid
GROUP BY 1 ORDER BY 1
"""

SCORE_SQL = """
SELECT LEAST(risk_score / 10, 9) * 10 AS bucket, count(*) AS calls
FROM call_decision GROUP BY 1 ORDER BY 1
"""

DIRECTION_SQL = """
SELECT COALESCE(direction, 'unknown') AS direction, count(*) AS calls
FROM call_record WHERE is_valid GROUP BY 1 ORDER BY 2 DESC
"""

INVALID_SQL = """
SELECT COALESCE(error_code, 'legacy') AS code, min(reason) AS sample, count(*) AS count
FROM invalid_cdr_row GROUP BY 1 ORDER BY 3 DESC
"""


def summary(db: Session) -> dict:
    row = dict(db.execute(text(SUMMARY_SQL)).mappings().one())
    row["avg_risk_score"] = float(row["avg_risk_score"] or 0)
    return row


def daily(db: Session) -> list[dict]:
    return [
        {"day": str(r["day"]), "count": r["call_count"], "blocked": r["blocked"],
         "review": r["review"], "allow": r["allow"]}
        for r in db.execute(text(DAILY_SQL)).mappings()
    ]


def hourly(db: Session) -> list[dict]:
    by_hour = {r["hour"]: dict(r) for r in db.execute(text(HOURLY_SQL)).mappings()}
    return [by_hour.get(h, {"hour": h, "calls": 0, "blocked": 0, "review": 0}) for h in range(24)]


def score_distribution(db: Session) -> list[dict]:
    by_bucket = {r["bucket"]: r["calls"] for r in db.execute(text(SCORE_SQL)).mappings()}
    return [{"bucket": f"{b}–{b + 9 if b < 90 else 100}", "from": b, "calls": by_bucket.get(b, 0)}
            for b in range(0, 100, 10)]


def factors(db: Session) -> list[dict]:
    from core.config import settings
    from services.ml_service import get_predictor
    from ml.feature_labels import LABELS
    importance = get_predictor(settings.ml_model_dir).metadata.get("feature_importance", {})
    return [{"code": k, "label": LABELS.get(k, k), "group": "model", "calls": round(v, 2), "points": round(v, 2)}
            for k, v in sorted(importance.items(), key=lambda pair: -pair[1])]


def directions(db: Session) -> list[dict]:
    return [dict(r) for r in db.execute(text(DIRECTION_SQL)).mappings()]


def invalid_reasons(db: Session) -> list[dict]:
    return [
        {"code": r["code"], "label": ERROR_LABELS.get(r["code"], r["sample"] or "причина не указана"),
         "count": r["count"]}
        for r in db.execute(text(INVALID_SQL)).mappings()
    ]
