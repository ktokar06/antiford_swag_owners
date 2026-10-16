import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.config import settings
from core.database import SessionLocal

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@router.get("/health/db")
def health_db():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db.execute(text("SELECT probability, model_version, feature_values FROM call_decision LIMIT 0"))
        from services.ml_service import get_predictor
        model = get_predictor(settings.ml_model_dir)
        return {"status": "ok", "db": "reachable", "schema": "ml_operator_v1",
                "engine": "catboost", "model_version": model.metadata["model_sha256"]}
    except Exception:
        log.exception("DB healthcheck failed")
        return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})
