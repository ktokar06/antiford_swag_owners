import pandas as pd

from ml.audit import find_candidates
from ml.features import build_features
from ml.weak_labels import label_scenarios
from tests.test_ml import call


def test_s4_counts_imsis_per_caller_with_overlaps():
    rows = [call(f"2024101412000{i}", imsi=f"2500112345678{i:02d}") for i in range(10)]
    frame = pd.DataFrame(rows)
    features = build_features(frame)

    assert features.iloc[4].caller_imsi_count_24h == 4
    assert features.iloc[4].caller_other_imsi_active == 4
    assert "S4" in set(find_candidates(frame).scenario)
    pd.testing.assert_frame_equal(features.iloc[:5], build_features(frame.iloc[:5]))


def test_victim_sequence_not_caller_sequence():
    rows = [call(f"2024101412000{i}", a=f"499000000{i}", duration=1) for i in range(4)]
    rows.append(call("20241014120100", a="0251234567", duration=900))
    f = build_features(pd.DataFrame(rows))

    assert f.iloc[-1].victim_short_city_sources_2h == 4
    assert find_candidates(pd.DataFrame(rows)).scenario.tolist() == ["S7"]


def test_d4_shared_destination_is_not_forward_chain():
    rows = []
    for i in range(30):
        row = call(f"202410141200{i:02d}", a=f"499000{i%10:04d}", duration=90)
        row.update(type="03", num_c="0259999999")
        rows.append(row)
    frame = pd.DataFrame(rows)
    candidates = find_candidates(frame)

    assert "D4" in set(candidates.scenario)
    assert "S5" not in set(candidates.scenario)
    assert build_features(frame).iloc[-1].forward_destination_source_count_24h == 10


def test_s2_sequential_targets_and_d5_random_targets():
    rows = []
    for i in range(40):
        date = (pd.Timestamp("2024-10-14 12:00") + pd.Timedelta(minutes=i)).strftime("%Y%m%d%H%M%S")
        rows.append(call(date, a="4991234567", b=f"025{i:07d}", duration=0 if i % 4 == 0 else 12))
    sequential = pd.DataFrame(rows)

    assert "S2" in set(find_candidates(sequential).scenario)
    assert "D5" not in set(find_candidates(sequential).scenario),

    random = sequential.copy()
    random["num_b"] = [f"025{i*7919:07d}" for i in range(40)]

    assert "D5" in set(find_candidates(random).scenario)
    assert "S2" not in set(find_candidates(random).scenario)


def test_callcenter_zero_calls_are_not_automatically_fraud():
    rows = []
    for i in range(40):
        date = (pd.Timestamp("2024-10-14 12:00") + pd.Timedelta(minutes=i)).strftime("%Y%m%d%H%M%S")
        rows.append(call(date, a="4991234567", b=f"025{i*7919:07d}", duration=0 if i < 14 else 90))
    rows.append(call("20241014110000", a="0259999999", b="4991234567"))
    frame = pd.DataFrame(rows)
    candidates = find_candidates(frame)

    assert "D1" in set(candidates.scenario)

    labels = label_scenarios(frame)

    assert labels.iloc[:40].label.eq(0).all()


def test_d2_requires_repeated_daily_waves():
    rows = []
    for day in (14, 15):
        for hour in (10, 16):
            for i in range(20):
                rows.append(call(f"202410{day}{hour}00{i:02d}", b=f"025{i*7919:07d}", duration=12))
    assert "D2" in set(find_candidates(pd.DataFrame(rows)).scenario)


def test_d3_requires_incoming_repeat_contacts_normal_duration():
    rows = []
    for i in range(20):
        hour = 2 if i < 12 else 12
        rows.append(call(f"20241014{hour:02d}{i:02d}00", b=f"025000000{i%3}", duration=90))
    rows.append(call("20241014010000", a="8999999999", b="0251234567"))
    assert "D3" in set(find_candidates(pd.DataFrame(rows)).scenario)


def test_s5_chain_follows_b_to_c():
    nodes = ["0251234567", "8991234567", "2001234567", "4991234567"]
    rows = []
    for i in range(3):
        row = call(f"2024101412000{i}", a="8429999999", b=nodes[i], duration=0)
        row.update(type="03", num_c=nodes[i+1])
        rows.append(row)
    assert find_candidates(pd.DataFrame(rows)).scenario.eq("S5").all()
    assert len(find_candidates(pd.DataFrame(rows))) == 3


def test_s6_closed_group_not_high_degree_star():
    numbers = [f"025000000{i}" for i in range(5)]
    rows = [call(f"20241014{hour:02d}0000", a=numbers[hour%5], b=numbers[(hour+1)%5], duration=20)
            for hour in range(24)]
    assert "S6" in set(find_candidates(pd.DataFrame(rows)).scenario)

    for i in range(10):
        rows.append(call(f"202410141200{i:02d}", a=numbers[0], b=f"899000000{i}"))
    assert "S6" not in set(find_candidates(pd.DataFrame(rows)).scenario)


def test_v1_artifact_remains_loadable():
    from pathlib import Path
    import pytest
    from ml.predict import Predictor
    path = Path(__file__).parents[1] / "artifacts/marked-v1"
    if not path.exists():
        pytest.skip("Локальный артефакт v1 отсутствует")
    result = Predictor(path).predict(pd.DataFrame([call("20241014120000")]), explain=True)
    assert len(result.iloc[0].explanation["factors"]) == 26


def test_scenario_history_expires_and_same_timestamp_is_invisible():
    frame = pd.DataFrame([
        call("20241014120000", imsi="250011234567890"),
        call("20241014120000", imsi="250011234567891"),
        call("20241015120001", imsi="250011234567892"),
    ])
    f = build_features(frame)
    assert f.caller_imsi_count_24h.tolist() == [0, 0, 0]
    assert f.caller_active_calls.tolist() == [0, 0, 0]


def test_conflicting_fraud_and_legitimate_candidates_abstain():
    rows = []
    for i in range(40):
        row = call(f"202410141200{i:02d}", a="4991234567", b=f"025{i*7919:07d}",
                   duration=0 if i < 14 else 90, imsi=f"2500112345678{i%4:02d}")
        rows.append(row)
    rows.append(call("20241014110000", a="0259999999", b="4991234567"))
    result = label_scenarios(pd.DataFrame(rows))
    assert result.iloc[:40].label.isna().all()
    assert result.iloc[:40].scenario.str.contains("D1").all()
    assert result.iloc[:40].scenario.str.contains("S4").all()
