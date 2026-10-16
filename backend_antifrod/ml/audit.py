"""Ретроспективный аудит наблюдаемых S/D-паттернов; не перезаписывает is_fraud.

Пороговые допуски — явная интерпретация текстового ТЗ. События в группах
анализируются целиком, поэтому этот модуль НЕ создаёт причинные ML-признаки.
"""
import argparse
import json
import logging
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from core.telecom import CITY_CODES, operator_group
from ml.data import load_records
from ml.scenarios import LEGITIMATE, SCENARIOS

log = logging.getLogger(__name__)


def prepare_frame(frame):
    f = frame.reset_index(drop=True).copy()
    f["timestamp"] = pd.to_datetime(f.date, format="%Y%m%d%H%M%S")
    f["duration"] = pd.to_numeric(f.duration)
    f["imsi"] = f.imsi.fillna("")
    f["num_c"] = f.num_c.fillna("")
    f["hour"] = f.timestamp.dt.hour
    f["day"] = f.timestamp.dt.date
    return f


def target_adjacency(numbers):
    values = np.sort(np.unique(np.asarray(numbers, dtype=np.int64)))
    return float(np.mean(np.diff(values) == 1)) if len(values) > 1 else 0.0


def find_candidates(frame):
    """Строки: position, scenario, evidence. Один CDR может иметь несколько сигналов.

    S1/S3/D2/D4/D5 проверяются только частично: CDR не содержит принадлежности
    компании/клиентской базе, тарифа или достоверной идентичности вызывающего.
    """
    f = prepare_frame(frame)
    evidence_rows = []

    def add(code, indices, evidence):
        evidence_rows.extend((int(i), code, evidence) for i in indices)

    incoming = f.groupby("num_b").size()
    # Суточные группы: произвольную смесь поведения за пять суток не считаем одним эпизодом.
    for (number, day), g in f.groupby(["num_a", "day"], sort=False):
        n = len(g)
        if n < 10:
            continue
        zero = float(g.duration.eq(0).mean())
        normal = float(g.duration.ge(30).mean())
        night = float(g.hour.lt(6).mean())
        unique = g.num_b.nunique()
        inbound = int(incoming.get(number, 0))
        city = number[:3] in CITY_CODES
        # D1 не отвергается из-за ожидаемых 35% нулевых вызовов.
        if city and n >= 30 and g.hour.between(8, 19).mean() >= .85 and normal >= .2 and inbound > 0 and .2 <= zero <= .5:
            add("D1", g.index, f"day={day}; calls={n}; zero_share={zero:.3f}; normal_share={normal:.3f}; incoming={inbound}")
        if .4 <= night <= .8 and inbound > 0 and unique / n <= .6 and normal >= .3:
            add("D3", g.index, f"day={day}; night_share={night:.3f}; unique_share={unique/n:.3f}; incoming={inbound}")
        if 300 <= unique <= 800 and g.duration.le(2).mean() >= .9:
            # Кандидат массовых коротких: доля 5% и платность C не доказаны.
            add("S1", g[g.duration.le(2)].index, f"day={day}; targets={unique}; short_share={g.duration.le(2).mean():.3f}; callback_not_verified")
        imsi_count = g.loc[g.imsi.ne(""), "imsi"].nunique()
        if 4 <= imsi_count <= 10:
            ordered = g.sort_values("timestamp")
            ends = ordered.timestamp + pd.to_timedelta(ordered.duration, unit="s")
            overlap = ordered.timestamp < ends.cummax().shift()
            if overlap.any():
                add("S4", g.index, f"day={day}; distinct_imsi={imsi_count}; overlapping_calls={int(overlap.sum())}")
        # По 2-часовым сессиям с перекрытием на час — границы фиксированы и задокументированы.
        for start_hour in range(23):
            episode = g[g.hour.between(start_hour, start_hour + 1)]
            if len(episode) < 30:
                continue
            span = (episode.timestamp.max() - episode.timestamp.min()).total_seconds()
            adjacency = target_adjacency(episode.num_b)
            ezero = float(episode.duration.eq(0).mean())
            expected = float((episode.duration.between(4, 25) | episode.duration.eq(0)).mean())
            if 1800 <= span <= 7200 and adjacency >= .8 and .1 <= ezero <= .4 and expected >= .9:
                add("S2", episode.index, f"day={day}; window_hour={start_hour}; adjacent_share={adjacency:.3f}; zero_share={ezero:.3f}")
        if city:
            for hour, episode in g.groupby("hour"):
                if len(episode) >= 30 and episode.num_b.nunique() / len(episode) >= .8 and target_adjacency(episode.num_b) <= .05:
                    add("D5", episode.index, f"day={day}; hour={hour}; calls={len(episode)}; random_targets_candidate; purpose_unknown")

    # D2: повторение 2–3 часовых пиков в несколько дней, а не один короткий звонок.
    for number, g in f.groupby("num_a", sort=False):
        if len(g) < 60 or g.day.nunique() < 2 or g.duration.between(6, 20).mean() < .8:
            continue
        peaks = []
        for _, day in g.groupby("day"):
            counts = day.hour.value_counts()
            hours = tuple(sorted(counts[counts >= max(10, len(day) * .15)].index))
            peaks.append(hours)
        if len(peaks) >= 2 and 2 <= len(peaks[0]) <= 3 and all(p == peaks[0] for p in peaks):
            if target_adjacency(g.num_b) < .2:
                add("D2", g.index, f"repeated_peak_hours={peaks[0]}; days={len(peaks)}; client_database_not_verified")

    for (destination, day), g in f[f.type.eq("03") & f.num_c.ne("")].groupby(["num_c", "day"]):
        sources = g.num_a.nunique()
        if 10 <= sources <= 30 and len(g) >= 30 and g.duration.ge(30).mean() >= .8:
            add("D4", g.index, f"day={day}; shared_forward_destination; sources={sources}; company_membership_unknown")

    # S6: слабосвязная компонента должна быть закрытой, а не просто иметь степень >=5.
    graph = nx.DiGraph()
    graph.add_edges_from(f[["num_a", "num_b"]].itertuples(index=False, name=None))
    candidates = [nodes for nodes in nx.weakly_connected_components(graph) if 5 <= len(nodes) <= 10]
    for nodes in candidates:
        g = f[f.num_a.isin(nodes)]
        if not g.empty and g.duration.between(8, 45).mean() >= .9 and g.hour.nunique() >= 20:
            add("S6", g.index, f"closed_component_size={len(nodes)}; active_hours={g.hour.nunique()}")

    # S5: связи именно B→C, в пределах минуты. Без call-id это кандидат общей цепочки.
    forwarded = f[f.type.eq("03") & f.num_c.ne("")]
    for minute, g in forwarded.groupby(forwarded.timestamp.dt.floor("min")):
        if len(g) < 3:
            continue
        graph = nx.DiGraph()
        graph.add_edges_from(g[["num_b", "num_c"]].itertuples(index=False, name=None))
        for nodes in nx.weakly_connected_components(graph):
            sub = graph.subgraph(nodes)
            # Три последовательных ребра или цикл. Звезда hotline не подходит.
            chain = any(len({a, b, v, w}) == 4 for a, b in sub.edges
                        for v in sub.successors(b) for w in sub.successors(v))
            cycle = not nx.is_directed_acyclic_graph(sub)
            if chain or cycle:
                rows = g[g.num_b.isin(nodes) & g.num_c.isin(nodes)]
                cross = rows.apply(lambda r: operator_group(r.num_b) != operator_group(r.num_c), axis=1)
                if cross.any():
                    add("S5", rows.index, f"minute={minute}; chain={chain}; cycle={cycle}; call_identity_unknown")

    # S7: жертва = B, а не инициатор. Смотрим только короткие предшествующие городские.
    for victim, g in f.groupby("num_b", sort=False):
        long_calls = g[g.duration.between(420, 1500)]
        short = g[g.duration.le(10) & g.num_a.str[:3].isin(CITY_CODES)]
        if short.num_a.nunique() < 4 or long_calls.empty:
            continue
        for i, row in long_calls.iterrows():
            preceding = short[(short.timestamp < row.timestamp) & (short.timestamp >= row.timestamp - pd.Timedelta(hours=2))]
            if 4 <= preceding.num_a.nunique() <= 8:
                add("S7", [i], f"preceding_city_sources={preceding.num_a.nunique()}; victim_sequence_2h; spoofing_not_verified")

    # S3: только индивидуальный профиль. Общий SIM-box из 3–8 SIM CDR не доказывает.
    for (imsi, day), g in f[f.imsi.ne("")].groupby(["imsi", "day"], sort=False):
        if len(g) < 30 or g.hour.nunique() < 20 or g.num_b.nunique() != len(g):
            continue
        if any(incoming.get(number, 0) for number in g.num_a.unique()):
            continue
        g = g.sort_values("timestamp")
        ends = g.timestamp + pd.to_timedelta(g.duration, unit="s")
        if not (g.timestamp < ends.cummax().shift()).any():
            add("S3", g.index, f"day={day}; active_hours={g.hour.nunique()}; unique_targets; no_overlap; sim_group_not_verified")
    return pd.DataFrame(evidence_rows, columns=["position", "scenario", "evidence"]).drop_duplicates(["position", "scenario"])


def audit(frame, output):
    findings = find_candidates(frame)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = frame.reset_index(drop=True)
    findings = findings.merge(records[["row_hash", "label"]] if "label" in records else records[["row_hash"]],
                              left_on="position", right_index=True, how="left")
    summary = {"rows": len(records), "interpretation": "retrospective_partial_candidates_not_ground_truth", "scenarios": {}}
    for code in [*SCENARIOS, *LEGITIMATE]:
        group = findings[findings.scenario.eq(code)]
        counts = pd.to_numeric(group.get("label", pd.Series(dtype=float)), errors="coerce").value_counts()
        summary["scenarios"][code] = {"candidate_rows": len(group), "label_0": int(counts.get(0, 0)), "label_1": int(counts.get(1, 0))}
    if "label" in findings:
        label = pd.to_numeric(findings.label, errors="coerce")
        findings["needs_review"] = (findings.scenario.str.startswith("D") & label.eq(1)) | (findings.scenario.str.startswith("S") & label.eq(0))
    findings.to_csv(output / "candidates.csv", sep=";", index=False)
    (output / "audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    log.info("Аудит: %s", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        records, _ = load_records(args.input)
        audit(records, args.output)
    except Exception:
        log.exception("Ошибка аудита сценариев")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
