"""
Загрузка CDR_OUT в БД.

Для каждого файла:
  1. SHA-256 содержимого — повторная загрузка того же файла пропускается;
     файл с тем же именем, но другим содержимым отклоняется (конфликт).
  2. Каждая строка проходит etl.cdr_parser.parse_line.
  3. Валидные строки через COPY попадают во временную таблицу, затем в call_record
     с ON CONFLICT (row_hash) DO NOTHING — дубликаты внутри файла и между файлами не вставляются.
  4. Невалидные строки сохраняются в invalid_cdr_row с кодом и текстом причины.
  5. В cdr_file пишется статистика: всего / валидных / дубликатов / невалидных.

Запуск: python -m etl.load_cdr [каталог]
"""
import hashlib
import csv
import io
import logging
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.models.call import CdrFile
from etl.cdr_parser import CdrError, CdrRecord, parse_line

log = logging.getLogger(__name__)

FILE_GLOB = "CDR_*.cdr"
MAX_RAW_LINE = 2000

STATUS_LOADED = "loaded"
STATUS_SKIPPED = "skipped_duplicate"
STATUS_CONFLICT = "conflict"

STAGE_DDL = """
CREATE TEMP TABLE IF NOT EXISTS stage_call (
    row_num INTEGER, type CHAR(2), imsi CHAR(15),
    caller_number CHAR(10), callee_number CHAR(10), forward_number CHAR(10),
    started_at TIMESTAMPTZ, duration_sec INTEGER, hung_up_first_second BOOLEAN,
    direction VARCHAR(20), connection_type VARCHAR(20), time_bucket VARCHAR(20),
    source_country VARCHAR(2), source_operator VARCHAR(10), foreign_origin BOOLEAN,
    row_hash CHAR(64)
) ON COMMIT DROP
"""

STAGE_COLUMNS = (
    "row_num, type, imsi, caller_number, callee_number, forward_number, started_at, "
    "duration_sec, hung_up_first_second, direction, connection_type, time_bucket, "
    "source_country, source_operator, foreign_origin, row_hash"
)

INSERT_FROM_STAGE = f"""
INSERT INTO call_record (cdr_file_id, {STAGE_COLUMNS}, is_valid)
SELECT :file_id, {STAGE_COLUMNS}, TRUE FROM stage_call ORDER BY row_num
ON CONFLICT (row_hash) DO NOTHING
"""


@dataclass
class LoadResult:
    filename: str
    status: str
    file_id: int | None = None
    rows_total: int = 0
    rows_valid: int = 0
    rows_duplicate: int = 0
    rows_invalid: int = 0
    message: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _record_row(row_num: int, r: CdrRecord) -> tuple:
    return (
        row_num, r.type, r.imsi, r.num_a, r.num_b, r.num_c, r.started_at,
        r.duration, r.hung_up_first_second, r.direction, r.connection_type, r.time_bucket,
        r.source_country, r.source_operator, r.foreign_origin, r.row_hash(),
    )


def _clean_raw(line: str) -> str:
    return line.rstrip("\r\n").replace("\x00", "")[:MAX_RAW_LINE]


def _find_existing(db: Session, filename: str, checksum: str) -> LoadResult | None:
    by_checksum = db.execute(select(CdrFile).where(CdrFile.checksum == checksum)).scalar_one_or_none()
    if by_checksum is not None:
        return LoadResult(
            filename=filename, status=STATUS_SKIPPED, file_id=by_checksum.id,
            message=f"Файл с таким содержимым уже загружен как {by_checksum.filename}",
        )
    by_name = db.execute(select(CdrFile).where(CdrFile.filename == filename)).scalar_one_or_none()
    if by_name is not None:
        return LoadResult(
            filename=filename, status=STATUS_CONFLICT, file_id=by_name.id,
            message="Файл с таким именем уже загружен, но содержимое отличается",
        )
    return None


def load_lines(db: Session, filename: str, checksum: str, lines: Iterable[str], source: str) -> LoadResult:
    """Загружает строки одного файла в рамках текущей транзакции (commit делает вызывающий)."""
    existing = _find_existing(db, filename, checksum)
    if existing is not None:
        return existing

    cdr = CdrFile(filename=filename, checksum=checksum, source=source, status=STATUS_LOADED)
    db.add(cdr)
    db.flush()

    db.execute(text(STAGE_DDL))
    db.execute(text("TRUNCATE stage_call"))

    total = valid = invalid = 0
    raw_conn = db.connection().connection  # psycopg3-соединение текущей транзакции
    with raw_conn.cursor() as cur:
        with cur.copy(f"COPY stage_call ({STAGE_COLUMNS}) FROM STDIN") as copy_valid:
            invalid_rows: list[tuple] = []
            for row_num, line in enumerate(lines, 1):
                parsed = parse_line(line)
                if parsed is None:
                    continue
                total += 1
                if isinstance(parsed, CdrError):
                    invalid += 1
                    invalid_rows.append((
                        cdr.id, row_num, _clean_raw(line), parsed.reason, parsed.code, parsed.fields_found,
                    ))
                    continue
                valid += 1
                copy_valid.write_row(_record_row(row_num, parsed))

        if invalid_rows:
            with cur.copy(
                "COPY invalid_cdr_row (cdr_file_id, row_num, raw_line, reason, error_code, fields_found) FROM STDIN"
            ) as copy_invalid:
                for row in invalid_rows:
                    copy_invalid.write_row(row)

    inserted = db.execute(text(INSERT_FROM_STAGE), {"file_id": cdr.id}).rowcount or 0

    cdr.rows_total = total
    cdr.rows_valid = inserted
    cdr.rows_duplicate = valid - inserted
    cdr.rows_invalid = invalid
    db.flush()

    return LoadResult(
        filename=filename, status=STATUS_LOADED, file_id=cdr.id,
        rows_total=total, rows_valid=inserted, rows_duplicate=valid - inserted, rows_invalid=invalid,
    )


def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_file(db: Session, path: Path, source: str = "directory") -> LoadResult:
    checksum = file_checksum(path)
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        return load_lines(db, path.name, checksum, csv_lines(fh) if path.suffix.lower() == ".csv" else fh, source)


def csv_lines(stream):
    from ml.data import RAW_FIELDS, CSV_ALIASES, normalize_csv_row
    reader = csv.DictReader(stream, delimiter=";")
    names = reader.fieldnames or []
    if not set(RAW_FIELDS) <= {CSV_ALIASES.get(k, k) for k in names}:
        raise ValueError("CSV: отсутствуют колонки CDR")
    for row in reader:
        row = normalize_csv_row(row, "is_fraud" in names and "phone_a" in names)
        yield ";".join(row.get(k) or "" for k in RAW_FIELDS)


def load_bytes(db: Session, filename: str, data: bytes, source: str = "upload") -> LoadResult:
    checksum = hashlib.sha256(data).hexdigest()
    decoded = data.decode("utf-8-sig", errors="replace")
    lines = csv_lines(io.StringIO(decoded)) if filename.lower().endswith(".csv") else decoded.splitlines()
    return load_lines(db, filename, checksum, lines, source)


def load_directory(db: Session, directory: Path | str | None = None) -> list[LoadResult]:
    directory = Path(directory or settings.cdr_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Каталог CDR не найден: {directory}")
    results = []
    files = sorted([*directory.glob(FILE_GLOB), *directory.glob("*.csv")])
    log.info("CDR: найдено файлов %d в %s", len(files), directory)
    for i, path in enumerate(files, 1):
        try:
            res = load_file(db, path)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("CDR: ошибка загрузки %s", path.name)
            res = LoadResult(filename=path.name, status="failed", message="Ошибка загрузки, см. логи backend")
        results.append(res)
        if i % 50 == 0 or i == len(files):
            log.info("CDR: %d/%d файлов обработано", i, len(files))
    return results


def summarize(results: list[LoadResult]) -> dict:
    out = {"files": len(results), "loaded": 0, "skipped": 0, "conflicts": 0, "failed": 0,
           "rows_valid": 0, "rows_duplicate": 0, "rows_invalid": 0}
    for r in results:
        key = {STATUS_LOADED: "loaded", STATUS_SKIPPED: "skipped", STATUS_CONFLICT: "conflicts"}.get(r.status, "failed")
        out[key] += 1
        out["rows_valid"] += r.rows_valid
        out["rows_duplicate"] += r.rows_duplicate
        out["rows_invalid"] += r.rows_invalid
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    directory = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        print(summarize(load_directory(db, directory)))
    finally:
        db.close()


if __name__ == "__main__":
    main()
