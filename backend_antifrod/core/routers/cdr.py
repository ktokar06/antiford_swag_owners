from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from core.config import settings
from core.deps import get_current_user, get_db_dep
from core.models.user import AppUser
from etl import pipeline
from services import cdr_service

router = APIRouter(prefix="/cdr", tags=["cdr"], dependencies=[Depends(get_current_user)])


@router.get("/files")
def list_files(
        search: str | None = Query(None, max_length=200),
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return cdr_service.list_files(db, {"search": search, "limit": limit, "offset": offset, "cursor": cursor})


@router.get("/valid")
def list_valid(
        cdr_file_id: int | None = None,
        type: str | None = Query(None, pattern="^0[123]$"),
        search: str | None = Query(None, max_length=40),
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return cdr_service.list_valid(db, {"cdr_file_id": cdr_file_id, "type": type, "search": search,
                                       "limit": limit, "offset": offset, "cursor": cursor})


@router.get("/invalid")
def list_invalid(
        cdr_file_id: int | None = None,
        error_code: str | None = Query(None, max_length=40),
        search: str | None = Query(None, max_length=60),
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return cdr_service.list_invalid(db, {"cdr_file_id": cdr_file_id, "error_code": error_code, "search": search,
                                         "limit": limit, "offset": offset, "cursor": cursor})


@router.post("/upload", status_code=201)
async def upload(
        file: UploadFile = File(...),
        db: Session = Depends(get_db_dep),
        _: AppUser = Depends(get_current_user),
):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
    result = await run_in_threadpool(cdr_service.upload, db, file.filename, data)
    if result["status"] == "loaded":
        result["pipeline"] = pipeline.start_background(load=False)
    return result


@router.post("/import", status_code=202)
def import_directory(_: AppUser = Depends(get_current_user)):
    """Загрузить все новые файлы из CDR_DIR и пересчитать скоринг (в фоне)."""
    return pipeline.start_background(load=True)


@router.get("/jobs/current")
def job_status():
    return pipeline.job_status()
