"""Совместимый ETL-адаптер кандидатов S1–S7 / D1–D5 по таблицам организаторов."""
from ml.audit import find_candidates
from ml.scenarios import LEGITIMATE, SCENARIOS


class FraudScenarioDetector:
    def __init__(self, df):
        self.df = df.reset_index(drop=True)

    def run(self):
        candidates = find_candidates(self.df)
        scores = {code: {} for code in SCENARIOS}
        flags = {code: {} for code in SCENARIOS}
        legitimate = {}
        for row in candidates.itertuples(index=False):
            number = self.df.iloc[row.position].num_a
            if row.scenario in SCENARIOS:
                flags[row.scenario][number] = 1
                scores[row.scenario][number] = {
                    "flag": 1, "score": 1.0, "evidence": row.evidence,
                    "interpretation": "candidate_not_confirmed",
                }
            elif row.scenario in LEGITIMATE:
                legitimate.setdefault(number, {})[row.scenario.lower()] = 1
        return scores, flags, legitimate
