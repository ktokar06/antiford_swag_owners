import pandas as pd
from sqlalchemy import delete, select

from core.database import SessionLocal
from core.models.call import CallRecord
from core.models.labeling import (
    FraudScenario, FalsePositiveLabel,
    PhoneNumberScenario, PhoneNumberFalsePositive,
)
from core.models.subscriber import PhoneNumber
from ml.labeling import FraudScenarioDetector
from ml.scenarios import SCENARIOS, LEGITIMATE as FPS


def ensure_reference(db):
    for code, (name, desc) in SCENARIOS.items():
        existing = db.execute(select(FraudScenario).where(FraudScenario.code == code)).scalar_one_or_none()
        if existing is None:
            db.add(FraudScenario(code=code, name=name, description=desc))
        else:
            existing.name, existing.description = name, desc
    for code, (name, desc) in FPS.items():
        existing = db.execute(select(FalsePositiveLabel).where(FalsePositiveLabel.code == code)).scalar_one_or_none()
        if existing is None:
            db.add(FalsePositiveLabel(code=code, name=name, description=desc))
        else:
            existing.name, existing.description = name, desc
    db.flush()


def load_raw(db) -> pd.DataFrame:
    rows = db.execute(select(
        CallRecord.id, CallRecord.type, CallRecord.imsi,
        CallRecord.caller_number, CallRecord.callee_number,
        CallRecord.started_at, CallRecord.duration_sec, CallRecord.forward_number,
    ).where(CallRecord.is_valid.is_(True))).all()
    df = pd.DataFrame(rows, columns=[
        "id", "type", "imsi", "num_a", "num_b", "started_at", "duration", "num_c",
    ])
    df["date"] = pd.to_datetime(df["started_at"]).dt.strftime("%Y%m%d%H%M%S")
    df["file"] = ""
    df["duration"] = df["duration"].astype(int)
    df["num_c"] = df["num_c"].fillna("")
    df["imsi"] = df["imsi"].fillna("")
    return df


def phone_id(db, number: str) -> int | None:
    if not number:
        return None
    row = db.execute(select(PhoneNumber).where(PhoneNumber.number == number)).scalar_one_or_none()
    return row.id if row else None


def persist_scenarios(db, flags, scores=None):
    for code, mapping in flags.items():
        scenario = db.execute(select(FraudScenario).where(FraudScenario.code == code)).scalar_one_or_none()
        if scenario is None:
            continue
        for num, flag in mapping.items():
            if not flag:
                continue
            pid = phone_id(db, num)
            if pid is None:
                continue
            if db.get(PhoneNumberScenario, (pid, scenario.id)) is None:
                db.add(PhoneNumberScenario(
                    phone_number_id=pid, scenario_id=scenario.id,
                    score=1.0, evidence=f"organizer candidate {code}; not confirmed; "
                    + ((scores or {}).get(code, {}).get(num, {}).get("evidence", "")),
                ))


def persist_fps(db, d_flags):
    for i in range(1, 6):
        code = f"D{i}"
        label = db.execute(select(FalsePositiveLabel).where(FalsePositiveLabel.code == code)).scalar_one_or_none()
        if label is None:
            continue
        for num, flags in d_flags.items():
            if not flags.get(f"d{i}"):
                continue
            pid = phone_id(db, num)
            if pid is None:
                continue
            if db.get(PhoneNumberFalsePositive, (pid, label.id)) is None:
                db.add(PhoneNumberFalsePositive(
                    phone_number_id=pid, label_id=label.id,
                    evidence=f"legitimate scenario candidate {code}; not confirmed",
                ))


def main():
    db = SessionLocal()
    try:
        ensure_reference(db)
        print("Читаю вызовы...")
        df = load_raw(db)
        print(f"Строк: {len(df)}")
        print("Детектирую кандидаты S1–S7 / D1–D5...")
        det = FraudScenarioDetector(df)
        scores, scenario_flags, d_flags = det.run()
        print("Пишу метки...")
        # Пересчитываем только метки, созданные этим ETL (включая старые ошибочные
        # значения S/D). Пользовательские evidence не удаляются.
        old_s = [f"detected {code}" for code in SCENARIOS]
        old_d = [f"false positive {code}" for code in FPS]
        db.execute(delete(PhoneNumberScenario).where(
            PhoneNumberScenario.evidence.in_(old_s) |
            PhoneNumberScenario.evidence.startswith("organizer candidate ")))
        db.execute(delete(PhoneNumberFalsePositive).where(
            PhoneNumberFalsePositive.evidence.in_(old_d) |
            PhoneNumberFalsePositive.evidence.startswith("legitimate scenario candidate ")))
        persist_scenarios(db, scenario_flags, scores)
        persist_fps(db, d_flags)
        db.commit()
        print("Готово.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
