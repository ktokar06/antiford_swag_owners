"""Проверки причинности, контрактов данных и сохранения модели; не оценка реального качества."""
import json
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("catboost", reason="Установите ml/requirements.txt для ML-тестов")
pytest.importorskip("sklearn", reason="Установите ml/requirements.txt для ML-тестов")

from ml.config import TrainConfig
from ml.data import attach_labels, load_records
from ml.evaluate import choose_threshold
from ml.features import build_features
from ml.predict import Predictor
from ml.train import temporal_split, train
from ml.weak_labels import label_scenarios


def call(date, a="0251234567", b="8991234567", duration=120, imsi=""):
    return {"row_hash": f"{date}:{a}:{b}:{duration}:{imsi}", "type": "02" if imsi else "01",
            "imsi": imsi, "num_a": a, "num_b": b, "num_c": "", "date": date, "duration": duration}


def test_features_use_strict_past_and_expire_window():
    records = pd.DataFrame([
        call("20241014120000", duration=0),
        call("20241014120000", b="8991234568", duration=5),
        call("20241014120010", duration=100),
        call("20241014140000", duration=60),
    ])
    features = build_features(records)
    assert features.history_calls.tolist() == [0, 0, 2, 0]
    assert features.loc[2, "history_unanswered_share"] == 0.5
    assert features.loc[2, "history_mean_duration"] == 2.5
    assert features.loc[2, "history_duration_std"] == 2.5
    assert features.loc[2, "history_unique_targets"] == 2
    pd.testing.assert_frame_equal(features.iloc[:3], build_features(records.iloc[:3]))


def test_reciprocity_and_shared_imsi_are_past_only():
    records = pd.DataFrame([
        call("20241014120000", a="8991234567", b="0251234567"),
        call("20241014120001", a="0251234568", imsi="250011234567890"),
        call("20241014120002", imsi="250011234567890"),
    ])
    last = build_features(records).iloc[-1]
    assert last.history_reverse_pair_calls == 1
    assert last.imsi_number_count == 1
    assert last.imsi_active_calls == 1


def test_parser_dedup_leading_zero_and_labels(tmp_path):
    source = tmp_path / "CDR_sample.cdr"
    valid = "01;;0251234567;8991234567;20241014120000;20;\n"
    source.write_text(valid + valid + "bad;line\n\n")
    frame, report = load_records(source)
    assert len(frame) == 1 and frame.iloc[0].num_a == "0251234567"
    assert report["duplicates"] == 1 and report["invalid"] == {"field_count": 1}
    labels = tmp_path / "labels.csv"
    labels.write_text("row_hash;label\n" + frame.iloc[0].row_hash + ";0\n")
    assert attach_labels(frame, labels).iloc[0].label == "0"
    labels.write_text(labels.read_text() + frame.iloc[0].row_hash + ";1\n")
    with pytest.raises(ValueError, match="повторяется"):
        attach_labels(frame, labels)


def test_temporal_split_never_separates_same_time():
    records = pd.DataFrame([call(f"20241014{hour:02d}0000") for hour in range(10) for _ in range(2)])
    split = temporal_split(records, TrainConfig())
    assert records.loc[split["train"], "date"].max() < records.loc[split["validation"], "date"].min()
    assert records.loc[split["validation"], "date"].max() < records.loc[split["test"], "date"].min()
    assert sum(mask.astype(int) for mask in split.values()).eq(1).all()


def test_threshold_respects_actual_rounded_scores():
    assert choose_threshold([0, 1], [0.804, 0.99], 0, 40) == 81
    assert choose_threshold([0, 1], [1, 1], 0, 40) == 101


def test_weak_label_does_not_equate_short_or_foreign_with_fraud():
    records = pd.DataFrame([call("20241014020000", a="7771234567", duration=1)])
    assert label_scenarios(records).label.isna().all()


def test_model_round_trip_and_shap(tmp_path):
    rows = []
    for i in range(120):
        date = (pd.Timestamp("2024-10-14") + pd.Timedelta(minutes=i)).strftime("%Y%m%d%H%M%S")
        row = call(date, a=f"025{i:07d}", duration=1 if i % 2 else 120)
        row.update(label=i % 2, scenario="test_fixture", label_source="test_fixture")
        rows.append(row)
    frame = pd.DataFrame(rows)
    output = tmp_path / "model"
    metrics = train(frame, output, TrainConfig(iterations=20, depth=2, early_stopping_rounds=5))
    assert metrics["test"]["rows"] == 24
    predictor = Predictor(output)
    prediction = predictor.predict(frame.tail(5), frame.iloc[:-5], explain=True)
    assert prediction.risk_score.between(0, 100).all()
    assert set(prediction.status) <= {"legitimate", "suspicious", "fraud"}
    assert np.allclose(prediction.probability, predictor.predict(frame).tail(5).probability)
    for row in prediction.to_dict("records"):
        explanation = row["explanation"]
        log_odds = explanation["base_log_odds"] + sum(f["contribution"] for f in explanation["factors"])
        assert np.isclose(1 / (1 + np.exp(-log_odds)), row["probability"])
    metadata = json.loads((output / "metadata.json").read_text())
    metadata["feature_version"] = -1
    (output / "metadata.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="версия"):
        Predictor(output)


def test_training_rejects_missing_labels(tmp_path):
    with pytest.raises(ValueError, match="Нет разметки"):
        train(pd.DataFrame([call("20241014120000")]), tmp_path / "model", TrainConfig())


def test_project_marked_schema_normalizes_export(tmp_path):
    source = tmp_path / "marked.csv"
    source.write_text(
        "type;imsi;phone_a;phone_b;time;duration;phone_c;is_fraud\n"
        "2;250020582732825.0;8109392353;2001413931;2026-10-01 00:00:00;3;;0\n"
        "3;;8109392353;2001413931;2026-10-01 00:00:01;3;255113701;1\n"
    )
    frame, _ = load_records(source)
    assert frame.iloc[0].imsi == "250020582732825"
    assert frame.iloc[0].type == "02"
    assert frame.iloc[1].num_c == "0255113701"
    assert frame.iloc[0].date == "20261001000000"
    assert frame.label.tolist() == ["0", "1"]
    assert frame.label_source.eq("hackathon_rules_user").all()


def test_conflicting_duplicate_labels_are_rejected(tmp_path):
    source = tmp_path / "marked.csv"
    row = "2;250020582732825.0;8109392353;2001413931;2026-10-01 00:00:00;3;;"
    source.write_text("type;imsi;phone_a;phone_b;time;duration;phone_c;is_fraud\n" + row + "0\n" + row + "1\n")
    with pytest.raises(ValueError, match="Противоречащие"):
        load_records(source)
