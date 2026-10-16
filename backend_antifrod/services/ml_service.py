"""ML-оценка CDR по модели и прошлой истории из существующей базы."""
from functools import lru_cache
import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from etl.cdr_parser import CdrError, parse_line

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_predictor(directory):
    from ml.predict import Predictor
    return Predictor(directory)


def score_envelope(db: Session, line: str, explain: bool) -> dict:
    record = parse_line(line)
    if record is None or isinstance(record, CdrError):
        raise HTTPException(422, record.reason if isinstance(record, CdrError) else "Пустой CDR")
    if not settings.ml_model_dir:
        raise HTTPException(503, "ML-модель не настроена: задайте ML_MODEL_DIR")
    try:
        predictor = get_predictor(settings.ml_model_dir)
    except Exception:
        log.exception("Не удалось загрузить ML-модель")
        raise HTTPException(503, "ML-модель недоступна") from None
    import pandas as pd
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    started_at = record.started_at.replace(tzinfo=ZoneInfo(settings.cdr_timezone))
    window = predictor.metadata["config"]["window_seconds"]
    history = pd.DataFrame(db.execute(text("""
        SELECT row_hash, type, COALESCE(imsi, '') AS imsi,
               caller_number AS num_a, callee_number AS num_b,
               COALESCE(forward_number, '') AS num_c,
               to_char(started_at, 'YYYYMMDDHH24MISS') AS date, duration_sec AS duration
        FROM call_record WHERE is_valid AND started_at >= :since AND started_at < :until
          AND (caller_number = :number OR callee_number = :number OR imsi = :imsi
               OR callee_number = :victim OR forward_number = :forward)
        ORDER BY started_at, id
    """), {"since": started_at - timedelta(seconds=max(window, 86400)), "until": started_at,
           "number": record.num_a, "imsi": record.imsi,
           "victim": record.num_b, "forward": record.num_c}).mappings().all())
    envelope = pd.DataFrame([{
        "row_hash": record.row_hash(), "type": record.type, "imsi": record.imsi or "",
        "num_a": record.num_a, "num_b": record.num_b, "num_c": record.num_c or "",
        "date": record.started_at.strftime("%Y%m%d%H%M%S"), "duration": record.duration,
    }])
    result = predictor.predict(envelope, history if not history.empty else None, explain).iloc[0].to_dict()
    result["model_created_at"] = predictor.metadata["created_at"]
    result["label_sources"] = predictor.metadata["label_sources"]
    return result
