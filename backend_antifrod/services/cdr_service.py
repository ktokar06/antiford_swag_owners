"""Просмотр загруженных CDR: файлы, валидные и невалидные записи; загрузка новых файлов."""
import re
from pathlib import PurePath

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core.models.call import CallRecord, CdrFile, InvalidCdrRow
from core.utils.pagination import digits_only, page, resolve_offset
from etl import load_cdr

FILENAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,200}$")


def _file_out(f: CdrFile) -> dict:
    return {
        "id": f.id, "filename": f.filename, "source": f.source, "status": f.status,
        "loaded_at": f.loaded_at, "rows_total": f.rows_total, "rows_valid": f.rows_valid,
        "rows_duplicate": f.rows_duplicate, "rows_invalid": f.rows_invalid,
    }


def list_files(db: Session, f: dict) -> dict:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    stmt = select(CdrFile)
    if f.get("search"):
        stmt = stmt.where(CdrFile.filename.ilike(f"%{f['search'].strip()}%"))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.execute(stmt.order_by(CdrFile.loaded_at.desc(), CdrFile.id.desc())
                      .offset(offset).limit(limit + 1)).scalars().all()
    rows, next_cursor, has_more = page(rows, limit, offset)
    return {"items": [_file_out(r) for r in rows], "total": total,
            "next_cursor": next_cursor, "has_more": has_more, "offset": offset}


def _valid_out(c: CallRecord, filename: str | None) -> dict:
    return {
        "id": c.id, "cdr_file_id": c.cdr_file_id, "filename": filename, "row_num": c.row_num,
        "type": c.type, "imsi": c.imsi, "num_a": c.caller_number, "num_b": c.callee_number,
        "num_c": c.forward_number, "started_at": c.started_at, "duration_sec": c.duration_sec,
        "direction": c.direction, "connection_type": c.connection_type,
    }


def list_valid(db: Session, f: dict) -> dict:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    stmt = select(CallRecord, CdrFile.filename).join(CdrFile, CdrFile.id == CallRecord.cdr_file_id, isouter=True)
    cnt = select(func.count()).select_from(CallRecord)
    conds = [CallRecord.is_valid.is_(True)]
    if f.get("cdr_file_id"):
        conds.append(CallRecord.cdr_file_id == f["cdr_file_id"])
    if f.get("type"):
        conds.append(CallRecord.type == f["type"])
    digits = digits_only(f.get("search"))
    if digits:
        conds.append(or_(CallRecord.caller_number.like(f"%{digits}%"),
                         CallRecord.callee_number.like(f"%{digits}%"),
                         CallRecord.imsi.like(f"%{digits}%")))
    stmt, cnt = stmt.where(*conds), cnt.where(*conds)
    rows = db.execute(stmt.order_by(CallRecord.id.desc()).offset(offset).limit(limit + 1)).all()
    rows, next_cursor, has_more = page(rows, limit, offset)
    return {"items": [_valid_out(c, fn) for c, fn in rows], "total": int(db.scalar(cnt) or 0),
            "next_cursor": next_cursor, "has_more": has_more, "offset": offset}


def list_invalid(db: Session, f: dict) -> dict:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    conds = []
    if f.get("cdr_file_id"):
        conds.append(InvalidCdrRow.cdr_file_id == f["cdr_file_id"])
    if f.get("error_code"):
        conds.append(InvalidCdrRow.error_code == f["error_code"])
    if f.get("search"):
        q = f["search"].strip()[:60].replace("%", r"\%").replace("_", r"\_")
        conds.append(InvalidCdrRow.raw_line.like(f"%{q}%"))
    stmt = (select(InvalidCdrRow, CdrFile.filename)
            .join(CdrFile, CdrFile.id == InvalidCdrRow.cdr_file_id, isouter=True).where(*conds))
    total = int(db.scalar(select(func.count()).select_from(InvalidCdrRow).where(*conds)) or 0)
    rows = db.execute(stmt.order_by(InvalidCdrRow.id.desc()).offset(offset).limit(limit + 1)).all()
    rows, next_cursor, has_more = page(rows, limit, offset)
    return {
        "items": [{
            "id": r.id, "cdr_file_id": r.cdr_file_id, "filename": fn, "row_num": r.row_num,
            "raw_line": r.raw_line, "reason": r.reason, "error_code": r.error_code,
            "fields_found": r.fields_found, "created_at": r.created_at,
        } for r, fn in rows],
        "total": total, "next_cursor": next_cursor, "has_more": has_more, "offset": offset,
    }


def safe_filename(name: str | None) -> str:
    base = PurePath(name or "").name
    if not FILENAME_RE.match(base) or not base.lower().endswith((".cdr", ".csv")):
        raise HTTPException(422, "Нужен файл .cdr или .csv; в имени — латиница, цифры, _ . -")
    return base


def upload(db: Session, filename: str, data: bytes) -> dict:
    name = safe_filename(filename)
    try:
        res = load_cdr.load_bytes(db, name, data)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e
    except Exception:
        db.rollback()
        raise
    if res.status == load_cdr.STATUS_CONFLICT:
        raise HTTPException(409, res.message)
    return res.as_dict()
