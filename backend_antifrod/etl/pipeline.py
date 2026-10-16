"""
Полный поток данных: CDR_OUT → call_record / invalid_cdr_row → признаки → граф → скоринг → статистика.

Запуск:
    python -m etl.pipeline            # загрузить каталог CDR_DIR и пересчитать всё
    python -m etl.pipeline --no-load  # только пересчёт по уже загруженным данным
"""
import argparse
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import text

from core.database import SessionLocal, engine
from etl import load_cdr
from etl.load_features import compute_number_features
from etl.refresh_graph import refresh_graph
from services import scoring_service, stats_service

log = logging.getLogger(__name__)

PIPELINE_LOCK_KEY = 4207151


@contextmanager
def pipeline_lock():
    """Межпроцессная блокировка: CLI и API не пересчитывают одновременно."""
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": PIPELINE_LOCK_KEY})
        yield
    finally:
        try:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": PIPELINE_LOCK_KEY})
        finally:
            conn.close()


def run_pipeline(load: bool = True, directory: str | None = None, on_stage=None) -> dict:
    stage = on_stage or (lambda name: log.info("pipeline: %s", name))
    result: dict = {}
    with pipeline_lock():
        db = SessionLocal()
        try:
            from services.ml_service import get_predictor
            from core.config import settings
            get_predictor(settings.ml_model_dir)
            if load:
                stage("load")
                result["load"] = load_cdr.summarize(load_cdr.load_directory(db, directory))
            stage("features")
            result["features"] = compute_number_features(db)
            db.commit()
            stage("scoring")
            result["scoring"] = scoring_service.score_calls(db)
            db.commit()
            stage("graph")
            result["graph"] = refresh_graph(db)
            db.commit()
            stage("stats")
            result["stats"] = stats_service.refresh_all(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    return result

_state_lock = threading.Lock()
_state: dict = {
    "running": False, "stage": None, "started_at": None, "finished_at": None,
    "result": None, "error": None, "pending": False, "pending_load": False,
}


def job_status() -> dict:
    with _state_lock:
        return dict(_state)


def _worker(load: bool, directory: str | None) -> None:
    def on_stage(name):
        with _state_lock:
            _state["stage"] = name
        log.info("pipeline: %s", name)

    while True:
        try:
            res = run_pipeline(load=load, directory=directory, on_stage=on_stage)
            err = None
        except Exception as e:  # noqa: BLE001 — статус уходит в API, трейс в лог
            log.exception("pipeline failed")
            res, err = None, f"{type(e).__name__}: {e}"[:500]
        with _state_lock:
            _state.update(result=res, error=err, finished_at=datetime.now(timezone.utc).isoformat())
            if _state["pending"]:
                load, directory = _state["pending_load"], None
                _state.update(pending=False, pending_load=False,
                              started_at=datetime.now(timezone.utc).isoformat())
                continue
            _state.update(running=False, stage=None)
            return


def start_background(load: bool = False, directory: str | None = None) -> dict:
    with _state_lock:
        if _state["running"]:
            _state["pending"] = True
            _state["pending_load"] = _state["pending_load"] or load
            return {"status": "queued"}
        _state.update(running=True, stage="queued", error=None, result=None,
                      started_at=datetime.now(timezone.utc).isoformat(), finished_at=None)
    threading.Thread(target=_worker, args=(load, directory), daemon=True, name="pipeline").start()
    return {"status": "started"}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--no-load", action="store_true", help="не загружать файлы, только пересчитать")
    p.add_argument("--dir", default=None, help="каталог CDR (по умолчанию CDR_DIR)")
    args = p.parse_args()
    print(run_pipeline(load=not args.no_load, directory=args.dir))


if __name__ == "__main__":
    main()
