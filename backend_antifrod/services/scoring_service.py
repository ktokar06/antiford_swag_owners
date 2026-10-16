"""Единственный движок риска: CatBoost. Политика переводит балл в действие."""
import logging

import pandas as pd
from psycopg.types.json import Jsonb
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from core.config import settings
from core.models.scoring import BlockingPolicy
from ml.evaluate import ratings
from ml.features import build_features
from services.ml_service import get_predictor

log = logging.getLogger(__name__)

NUMBER_RISK_UPDATE = """
UPDATE number_feature nf SET max_risk_score=COALESCE(r.max_score,0), avg_risk_score=COALESCE(r.avg_score,0)
FROM phone_number pn LEFT JOIN (
 SELECT c.caller_number, max(d.risk_score) max_score, avg(d.risk_score) avg_score
 FROM call_record c JOIN call_decision d ON d.call_id=c.id GROUP BY c.caller_number
) r ON r.caller_number=pn.number WHERE nf.phone_number_id=pn.id
"""


def get_active_policy(db: Session) -> BlockingPolicy:
    policy = db.execute(select(BlockingPolicy).where(BlockingPolicy.is_active.is_(True))).scalar_one_or_none()
    if policy is None:
        policy = BlockingPolicy(name="Политика ML", is_active=True)
        db.add(policy)
        db.flush()
    return policy


def decide(score: int, policy: BlockingPolicy) -> str:
    if policy.auto_block_enabled and score >= policy.auto_block_threshold:
        return "auto_blocked"
    return "review" if score >= policy.review_threshold else "allow"


def score_calls(db: Session) -> dict:
    predictor = get_predictor(settings.ml_model_dir)
    policy = get_active_policy(db)
    records = pd.DataFrame(db.execute(text("""
        SELECT id, row_hash, type, coalesce(imsi,'') imsi, caller_number num_a,
               callee_number num_b, coalesce(forward_number,'') num_c,
               to_char(started_at,'YYYYMMDDHH24MISS') date, duration_sec duration
        FROM call_record WHERE is_valid ORDER BY started_at,id
    """)).mappings().all())
    if records.empty:
        return {"scored_calls": 0, "engine": "catboost"}
    features = build_features(records, predictor.metadata["config"]["window_seconds"], predictor.metadata["feature_version"])
    db.execute(text("CREATE TEMP TABLE stage_prediction (call_id bigint, risk_score int, decision varchar(20), probability double precision, model_version varchar(64), feature_values jsonb, policy_id int) ON COMMIT DROP"))
    version = predictor.metadata["model_sha256"]
    raw = db.connection().connection
    with raw.cursor() as cursor:
        with cursor.copy("COPY stage_prediction FROM STDIN") as copy:
            for start in range(0, len(records), 10000):
                batch = features.iloc[start:start+10000]
                probability = predictor.model.predict_proba(batch, thread_count=4)[:, 1]
                scores = ratings(probability)
                for cid, score, p, values in zip(records.id.iloc[start:start+10000], scores, probability, batch.itertuples(index=False, name=None)):
                    copy.write_row((int(cid), int(score), decide(int(score), policy), float(p), version, Jsonb(list(values)), policy.id))
        db.execute(text("DELETE FROM call_risk_factor"))
    db.execute(text("DELETE FROM call_decision"))
    db.execute(text("""INSERT INTO call_decision (call_id,risk_score,decision,probability,model_version,feature_values,policy_id)
        SELECT call_id,risk_score,decision,probability,model_version,feature_values,policy_id FROM stage_prediction"""))
    db.execute(text(NUMBER_RISK_UPDATE))
    db.execute(text("""INSERT INTO call_review(call_id,status_code,updated_at)
        SELECT call_id,'pending',now() FROM call_decision WHERE decision IN ('review','auto_blocked')
        ON CONFLICT(call_id) DO NOTHING"""))
    log.info("CatBoost: сохранено %s предсказаний, модель %s", len(records), version[:12])
    return {"scored_calls": len(records), "engine": "catboost", "model_version": version}
