from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from services.ml_service import score_envelope
from services.ml_service import get_predictor
from core.config import settings

router = APIRouter(prefix="/ml", tags=["ml"], dependencies=[Depends(get_current_user)])


@router.get("/model")
def model_info():
    from pathlib import Path
    import json
    predictor = get_predictor(settings.ml_model_dir)
    metrics_path = Path(settings.ml_model_dir) / "metrics.json"
    return {"engine": "catboost", **predictor.metadata,
            "metrics": json.loads(metrics_path.read_text()) if metrics_path.exists() else {}}


class EnvelopeIn(BaseModel):
    cdr_line: str = Field(min_length=1, max_length=500)
    explain: bool = True


@router.post("/score")
def score(data: EnvelopeIn, db: Session = Depends(get_db_dep)):
    return score_envelope(db, data.cdr_line, data.explain)
