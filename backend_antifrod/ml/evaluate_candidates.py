"""Ошибки модели на ретроспективных S/D-кандидатах отложенной части marked."""
import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from ml.data import load_records
from ml.evaluate import evaluate
from ml.predict import Predictor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--candidates", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        model = Path(args.model)
        predictor = Predictor(model)
        records, _ = load_records(args.input)
        split = pd.read_csv(model / "split.csv", sep=";", usecols=["row_hash", "split"])
        test_hashes = set(split.loc[split.split.eq("test"), "row_hash"])
        test = records[records.row_hash.isin(test_hashes)]
        probabilities = predictor.predict(test, records)[["row_hash", "probability"]]
        candidate = pd.read_csv(args.candidates, sep=";", usecols=["row_hash", "scenario"])
        joined = candidate.merge(probabilities, on="row_hash").merge(
            records[["row_hash", "label"]], on="row_hash", validate="many_to_one")
        reports = {}
        for scenario, group in joined.groupby("scenario"):
            y = pd.to_numeric(group.label).astype(int)
            reports[scenario] = evaluate(y, group.probability, predictor.metadata["block_threshold"])
            reports[scenario]["review_or_fraud"] = evaluate(y, group.probability, predictor.metadata["config"]["review_threshold"])
        report = {"interpretation": "metrics_against_existing_labels_on_partial_candidate_cohorts", "cohorts": reports}
        (model / "candidate_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        logging.info("Когорты test: %s", {k: v["rows"] for k, v in reports.items()})
    except Exception:
        logging.exception("Не удалось оценить кандидатов")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
