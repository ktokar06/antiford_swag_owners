"""Кандидаты по таблицам организаторов, без подмены существующей разметки."""
import pandas as pd

from ml.audit import find_candidates


def label_scenarios(records: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=range(len(records)), columns=["label", "scenario"])
    result["label_source"] = "organizer_scenario_candidates_v2"
    candidates = find_candidates(records)
    for position, group in candidates.groupby("position"):
        codes = sorted(set(group.scenario))
        fraud = any(c.startswith("S") for c in codes)
        legitimate = any(c.startswith("D") for c in codes)
        result.loc[position, "scenario"] = ",".join(codes)
        # Пересечение D и S оставляем оператору; отсутствие кандидата тоже не класс 0.
        if fraud != legitimate:
            result.loc[position, "label"] = int(fraud)
    return result
