"""Единая валидация CDR/CSV и чтение подтверждённых вердиктов из БД."""
import csv
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

from etl.cdr_parser import CdrError, parse_line

log = logging.getLogger(__name__)
RAW_FIELDS = ["type", "imsi", "num_a", "num_b", "date", "duration", "num_c"]
REVIEW_TARGETS = {"confirmed_fraud": 1, "false_positive": 0, "cleared": 0}
CSV_ALIASES = {
    "call_type": "type", "imsi_a": "imsi", "number_a": "num_a", "number_b": "num_b",
    "start_call": "date", "number_c": "num_c", "phone_a": "num_a", "phone_b": "num_b",
    "time": "date", "phone_c": "num_c", "is_fraud": "label",
}


def normalize_csv_row(row, marked=False):
    row = {CSV_ALIASES.get(k, k): v for k, v in row.items()}
    if marked:
        row["type"] = row["type"].zfill(2)
        for key in ("imsi", "num_a", "num_b", "num_c"):
            value = row.get(key, "") or ""
            value = value.removesuffix(".0")
            if value and value.isascii() and value.isdigit() and key != "imsi":
                value = value.zfill(10)
            row[key] = value
        row["date"] = row["date"].replace("-", "").replace(" ", "").replace(":", "")
        row["label_source"] = "hackathon_rules_user"
    return row


def load_records(source: str | Path) -> tuple[pd.DataFrame, dict]:
    source = Path(source)
    paths = sorted(source.glob("CDR_*.cdr")) if source.is_dir() else [source]
    if not paths:
        raise ValueError(f"Нет CDR_*.cdr в {source}")
    rows, seen, errors = [], {}, Counter()
    duplicates = blank = 0
    for path in paths:
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
            if path.suffix.lower() == ".csv":
                reader = csv.DictReader(stream, delimiter=";")
                names = reader.fieldnames or []
                if not set(RAW_FIELDS) <= {CSV_ALIASES.get(k, k) for k in names}:
                    raise ValueError(f"{path}: нужны CSV-колонки {RAW_FIELDS}")
                marked = "is_fraud" in names and "phone_a" in names
                normalized = (normalize_csv_row(row, marked) for row in reader)
                lines = ((i, ";".join(row.get(k) or "" for k in RAW_FIELDS), row)
                         for i, row in enumerate(normalized, 2))
            else:
                lines = ((i, line, {}) for i, line in enumerate(stream, 1))
            for line_number, line, extra in lines:
                record = parse_line(line)
                if record is None:
                    blank += 1
                    continue
                if isinstance(record, CdrError):
                    errors[record.code] += 1
                    continue
                key = record.row_hash()
                if key in seen:
                    previous_label = seen[key]
                    label = extra.get("label")
                    if previous_label and label and float(previous_label) != float(label):
                        raise ValueError(f"Противоречащие метки дубликата CDR: {key}")
                    duplicates += 1
                    continue
                seen[key] = extra.get("label")
                rows.append({
                    "row_hash": key, "type": record.type, "imsi": record.imsi or "",
                    "num_a": record.num_a, "num_b": record.num_b, "num_c": record.num_c or "",
                    "date": record.started_at.strftime("%Y%m%d%H%M%S"), "duration": record.duration,
                    "file": path.name, "row_num": line_number,
                    **{k: extra[k] for k in ("label", "scenario", "label_source") if extra.get(k)},
                })
                if len(rows) % 250000 == 0:
                    log.info("Прочитано %s валидных CDR", len(rows))
    if not rows:
        raise ValueError("Нет валидных CDR для обработки")
    report = {"files": len(paths), "valid": len(rows), "duplicates": duplicates,
              "blank": blank, "invalid": dict(errors)}
    log.info("Подготовлены CDR: %s", report)
    return pd.DataFrame(rows), report


def load_database() -> tuple[pd.DataFrame, dict]:
    # Отложенные импорты: файловое обучение не требует DATABASE_URL/JWT_SECRET.
    from sqlalchemy import text
    from core.database import engine
    query = text("""
        SELECT c.row_hash, c.type, COALESCE(c.imsi, '') AS imsi,
               c.caller_number AS num_a, c.callee_number AS num_b,
               COALESCE(c.forward_number, '') AS num_c,
               to_char(c.started_at, 'YYYYMMDDHH24MISS') AS date,
               c.duration_sec AS duration, r.status_code AS review_status
        FROM call_record c LEFT JOIN call_review r ON r.call_id = c.id
        WHERE c.is_valid ORDER BY c.started_at, c.id
    """)
    with engine.connect() as connection:
        frame = pd.read_sql(query, connection)
    if frame.empty:
        raise ValueError("В БД нет валидных CDR")
    frame["label"] = frame.pop("review_status").map(REVIEW_TARGETS)
    frame["label_source"] = "operator_review"
    return frame, {"source": "database", "valid": len(frame)}


def attach_labels(frame: pd.DataFrame, path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return frame
    labels = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    if not {"row_hash", "label"} <= set(labels):
        raise ValueError("Разметка должна содержать row_hash;label (0 или 1)")
    if labels.row_hash.duplicated().any():
        raise ValueError("В разметке повторяется row_hash; устраните неоднозначные вердикты")
    if not labels.label.isin(["0", "1"]).all():
        raise ValueError("label в файле разметки должен быть 0 или 1")
    unknown = ~labels.row_hash.isin(frame.row_hash)
    if unknown.any():
        log.warning("%s меток не соответствуют загруженным CDR", int(unknown.sum()))
    columns = [c for c in ("row_hash", "label", "scenario", "label_source") if c in labels]
    return frame.drop(columns=[c for c in columns if c != "row_hash" and c in frame]).merge(
        labels[columns], on="row_hash", how="left", validate="one_to_one")
