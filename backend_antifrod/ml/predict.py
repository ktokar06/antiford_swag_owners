"""Загрузка версионированной модели; CDR → вероятность, рейтинг 0..100, статус."""
import argparse
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from ml.config import TrainConfig
from ml.data import load_records
from ml.evaluate import ratings
from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, V1_FEATURE_COLUMNS, build_features


class Predictor:
    def __init__(self, directory: str | Path):
        directory = Path(directory)
        self.metadata = json.loads((directory / "metadata.json").read_text())
        config = TrainConfig(**self.metadata["config"])
        if not config.review_threshold < self.metadata["block_threshold"] <= 101:
            raise ValueError("Некорректный порог модели")
        version = self.metadata["feature_version"]
        self.feature_columns = V1_FEATURE_COLUMNS if version == 1 else FEATURE_COLUMNS
        if (version not in (1, 2)
                or self.metadata["features"] != self.feature_columns
                or self.metadata["categorical_features"] != CATEGORICAL_FEATURES):
            raise ValueError("Несовместимая версия признаков модели")
        model_path = directory / "model.cbm"
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != self.metadata["model_sha256"]:
            raise ValueError("Контрольная сумма модели не совпадает")
        self.model = CatBoostClassifier()
        self.model.load_model(str(model_path))
        if self.model.feature_names_ != self.feature_columns or list(self.model.classes_) != [0, 1]:
            raise ValueError("Схема модели не совпадает с метаданными")

    def predict(self, records: pd.DataFrame, history: pd.DataFrame | None = None,
                explain: bool = False) -> pd.DataFrame:
        if records.empty:
            raise ValueError("Нет CDR для классификации")
        all_records = pd.concat([records, history], ignore_index=True) if history is not None else records.copy()
        all_records = all_records.drop_duplicates("row_hash").reset_index(drop=True)
        features = build_features(all_records, self.metadata["config"]["window_seconds"], self.metadata["feature_version"])
        positions = pd.Series(np.arange(len(all_records)), index=all_records.row_hash)
        selected = features.iloc[positions.loc[records.row_hash].to_numpy()].reset_index(drop=True)
        probability = self.model.predict_proba(selected)[:, 1]
        scores = ratings(probability)
        statuses = np.where(scores >= self.metadata["block_threshold"], "fraud",
                            np.where(scores >= self.metadata["config"]["review_threshold"], "suspicious", "legitimate"))
        result = pd.DataFrame({"row_hash": records.row_hash.to_numpy(), "probability": probability,
                               "risk_score": scores, "status": statuses})
        if explain:
            from ml.explain import explain_features
            result["explanation"] = explain_features(self.model, selected)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--history", help="Предыдущие CDR для поведенческих признаков")
    parser.add_argument("--output", required=True)
    parser.add_argument("--explain", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        records, _ = load_records(args.input)
        history = load_records(args.history)[0] if args.history else None
        result = Predictor(args.model).predict(records, history, args.explain)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.to_json(output, orient="records", force_ascii=False, indent=2)
        logging.info("Классифицировано %s CDR; результат: %s", len(result), output)
    except Exception:
        logging.exception("Классификация завершилась ошибкой")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
