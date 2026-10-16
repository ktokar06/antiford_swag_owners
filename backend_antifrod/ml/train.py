"""Обучение CatBoost на конвертах CDR с временным holdout."""
import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import catboost
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

from ml.config import TrainConfig
from ml.data import attach_labels, load_records
from ml.evaluate import choose_threshold, evaluate
from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, FEATURE_VERSION, build_features

log = logging.getLogger(__name__)


def temporal_split(frame, config):
    """Целые timestamp-группы: train раньше validation, validation раньше test."""
    times = sorted(frame.date.unique())
    train_end = int(len(times) * (1 - config.test_fraction - config.validation_fraction))
    validation_end = int(len(times) * (1 - config.test_fraction))
    if not 0 < train_end < validation_end < len(times):
        raise ValueError("Недостаточно различных времён для train/validation/test")
    return {
        "train": frame.date < times[train_end],
        "validation": (frame.date >= times[train_end]) & (frame.date < times[validation_end]),
        "test": frame.date >= times[validation_end],
    }


def train(frame: pd.DataFrame, output: str | Path, config: TrainConfig) -> dict:
    if "label" not in frame:
        raise ValueError("Нет разметки. Нужен label=0/1 из проверенных сценариев или call_review")
    frame = frame.reset_index(drop=True).copy()
    raw_labels = frame.label.replace("", np.nan)
    frame["label"] = pd.to_numeric(raw_labels, errors="coerce")
    if (raw_labels.notna() & frame.label.isna()).any() or not frame.label.dropna().isin([0, 1]).all():
        raise ValueError("label должен быть 0 (легитимный), 1 (фрод) или пустым (не размечен)")
    if frame.row_hash.duplicated().any():
        raise ValueError("Перед обучением удалите дубликаты CDR")
    splits = temporal_split(frame, config)
    masks = {name: mask & frame.label.notna() for name, mask in splits.items()}
    for name, mask in masks.items():
        if set(frame.loc[mask, "label"].astype(int)) != {0, 1}:
            raise ValueError(f"{name}: необходимы оба класса. Добавьте разметку или измените доли разбиения")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Каталог модели уже содержит файлы; укажите новый каталог версии")
    features = build_features(frame, config.window_seconds)
    model = CatBoostClassifier(
        iterations=config.iterations, depth=config.depth, learning_rate=config.learning_rate,
        random_seed=config.random_seed, thread_count=config.thread_count, loss_function="Logloss",
        eval_metric="Logloss", allow_writing_files=False, verbose=False,
    )
    log.info("Обучение: %s", {name: int(mask.sum()) for name, mask in masks.items()})
    model.fit(
        features.loc[masks["train"]], frame.loc[masks["train"], "label"].astype(int),
        cat_features=CATEGORICAL_FEATURES,
        eval_set=(features.loc[masks["validation"]], frame.loc[masks["validation"], "label"].astype(int)),
        early_stopping_rounds=config.early_stopping_rounds,
    )
    validation_probability = model.predict_proba(features.loc[masks["validation"]])[:, 1]
    threshold = choose_threshold(frame.loc[masks["validation"], "label"], validation_probability,
                                 config.max_false_positive_rate, config.review_threshold)
    metrics = {}
    for name in ("validation", "test"):
        mask = masks[name]
        probability = model.predict_proba(features.loc[mask])[:, 1]
        scenarios = frame.loc[mask, "scenario"] if "scenario" in frame else None
        metrics[name] = evaluate(frame.loc[mask, "label"], probability, threshold, scenarios)
        metrics[name]["review_or_block"] = evaluate(
            frame.loc[mask, "label"], probability, config.review_threshold, scenarios)
    metadata = {
        "feature_version": FEATURE_VERSION, "features": FEATURE_COLUMNS,
        "categorical_features": CATEGORICAL_FEATURES,
        "config": config.to_dict(), "block_threshold": threshold,
        "created_at": datetime.now(timezone.utc).isoformat(), "catboost_version": catboost.__version__,
        "label_sources": sorted(frame.get("label_source", pd.Series(["external_unspecified"])).dropna().unique().tolist()),
        "split_strategy": "chronological; strictly past metadata; unlabelled rows excluded from targets",
        "splits": {name: {"rows": int(mask.sum()), "from": str(frame.loc[mask, "date"].min()),
                          "to": str(frame.loc[mask, "date"].max())} for name, mask in masks.items()},
        "unlabelled_rows": int(frame.label.isna().sum()),
        "feature_importance": dict(zip(FEATURE_COLUMNS, map(float, model.feature_importances_))),
    }
    output.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output / "model.cbm"))
    metadata["model_sha256"] = hashlib.sha256((output / "model.cbm").read_bytes()).hexdigest()
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False))
    manifest = frame[["row_hash", "date", "label"]].copy()
    manifest["split"] = ""
    for name, mask in splits.items():
        manifest.loc[mask, "split"] = name
    manifest.to_csv(output / "split.csv", sep=";", index=False)
    log.info("Модель сохранена: %s; test: %s", output, metrics["test"])
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--labels")
    parser.add_argument("--config")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = TrainConfig.load(args.config)
        frame, report = load_records(args.input)
        train(attach_labels(frame, args.labels), args.output, config)
        (Path(args.output) / "data_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception:
        log.exception("Обучение завершилось ошибкой")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
