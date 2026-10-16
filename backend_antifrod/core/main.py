import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import SessionLocal
from core.routers import auth, blocks, calls, cdr, graph, health, ml, numbers, rules, stats
from core.utils.logging import setup_logging
from etl import pipeline
from services import auth_service

setup_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.ml_service import get_predictor
    get_predictor(settings.ml_model_dir)
    # Полная схема создаётся PostgreSQL из db/001_schema.sql при первом запуске.
    with SessionLocal() as db:
        auth_service.ensure_operator(db)
    if settings.cdr_autoload:
        log.info("CDR_AUTOLOAD: загрузка каталога %s в фоне", settings.cdr_dir)
        pipeline.start_background(load=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,  # токен передаётся в заголовке Authorization, cookies не используются
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
for r in (auth, calls, numbers, graph, blocks, rules, stats, cdr, ml):
    app.include_router(r.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "version": settings.app_version, "docs": "/docs", "health": "/health"}
