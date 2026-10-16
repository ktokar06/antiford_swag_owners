"""Признаки конверта и истории [t-window, t), без будущих звонков и идентификаторов в X."""
from collections import Counter, defaultdict, deque
from itertools import groupby
import logging

import numpy as np
import pandas as pd

from core.telecom import operator_group
from ml.scenario_features import SCENARIO_FEATURES, ScenarioHistory

FEATURE_VERSION = 2
CATEGORICAL_FEATURES = ["type", "source_group", "destination_group"]
NUMERIC_FEATURES = [
    "duration", "hour", "weekday", "is_night", "is_short", "is_unanswered", "is_forwarded",
    "has_imsi", "cross_operator", "history_calls", "history_unique_targets", "history_regions",
    "history_short_share", "history_unanswered_share", "history_mean_duration",
    "history_duration_std", "history_incoming", "history_reciprocal_share",
    "history_pair_calls", "history_reverse_pair_calls", "seconds_since_previous",
    "imsi_number_count", "imsi_active_calls",
]
V1_FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
FEATURE_COLUMNS = V1_FEATURE_COLUMNS + SCENARIO_FEATURES


class History:
    def __init__(self):
        self.calls = deque()
        self.targets = Counter()
        self.regions = Counter()
        self.total = self.squared = self.short = self.unanswered = 0

    def expire(self, cutoff):
        while self.calls and self.calls[0][0] < cutoff:
            _, target, duration = self.calls.popleft()
            self.targets[target] -= 1
            self.regions[target[:3]] -= 1
            if not self.targets[target]:
                del self.targets[target]
            if not self.regions[target[:3]]:
                del self.regions[target[:3]]
            self.total -= duration
            self.squared -= duration * duration
            self.short -= duration <= 10
            self.unanswered -= duration == 0

    def add(self, timestamp, target, duration):
        self.calls.append((timestamp, target, duration))
        self.targets[target] += 1
        self.regions[target[:3]] += 1
        self.total += duration
        self.squared += duration * duration
        self.short += duration <= 10
        self.unanswered += duration == 0


def build_features(frame: pd.DataFrame, window_seconds: int = 3600, version: int = FEATURE_VERSION) -> pd.DataFrame:
    """Одна строка результата на CDR, исходный порядок сохранён.

    История включает только звонки с более ранним started_at. Одновременные
    события обрабатываются группой. Длительность текущего CDR известна, поэтому
    модель предназначена для анализа завершённых вызовов.
    """
    if frame.empty:
        raise ValueError("Пустой набор CDR")
    if version not in (1, 2):
        raise ValueError("Неизвестная версия признаков")
    if window_seconds <= 0:
        raise ValueError("window_seconds должен быть положительным")
    work = frame.reset_index(drop=True).copy()
    work["timestamp"] = pd.to_datetime(work["date"], format="%Y%m%d%H%M%S", errors="raise")
    work["duration"] = pd.to_numeric(work.duration, errors="raise")
    if not np.isfinite(work.duration).all() or not work.duration.between(0, 86400).all():
        raise ValueError("Некорректная длительность CDR")
    work["imsi"] = work.imsi.fillna("")
    work["num_c"] = work.num_c.fillna("")
    work["position"] = np.arange(len(work))
    outgoing, incoming, imsis = defaultdict(History), defaultdict(History), defaultdict(History)
    active = defaultdict(list)
    numeric = np.zeros((len(work), len(NUMERIC_FEATURES)), dtype=np.float32)
    scenario_history = ScenarioHistory() if version == 2 else None
    scenario_values = np.zeros((len(work), len(SCENARIO_FEATURES)), dtype=np.float32) if version == 2 else None
    source_groups = work.num_a.str[:3].map(lambda p: operator_group(p) or "unknown")
    destination_groups = work.num_b.str[:3].map(lambda p: operator_group(p) or "unknown")
    records = work.sort_values(["timestamp", "position"])[
        ["timestamp", "position", "num_a", "num_b", "imsi", "duration", "type", "num_c"]
    ].itertuples(index=False, name=None)
    processed = 0
    for timestamp, batch in groupby(records, key=lambda r: r[0]):
        batch = list(batch)
        seconds = timestamp.value // 10**9
        cutoff = seconds - window_seconds
        for _, position, a, b, imsi, duration, type_, c in batch:
            if scenario_history is not None:
                scenario_values[position] = scenario_history.values(seconds, a, b, imsi, c)
            history, inbound = outgoing[a], incoming[a]
            history.expire(cutoff)
            inbound.expire(cutoff)
            n = len(history.calls)
            mean = history.total / n if n else 0
            group_a, group_b = operator_group(a) or "unknown", operator_group(b) or "unknown"
            imsi_count = active_count = 0
            if imsi:
                imsis[imsi].expire(cutoff)
                imsi_count = len(imsis[imsi].targets)
                active[imsi] = [end for end in active[imsi] if end > seconds]
                active_count = len(active[imsi])
            values = {
                "duration": duration, "hour": timestamp.hour, "weekday": timestamp.dayofweek,
                "is_night": int(timestamp.hour < 6), "is_short": int(duration <= 10),
                "is_unanswered": int(duration == 0), "is_forwarded": int(type_ == "03"),
                "has_imsi": int(bool(imsi)), "cross_operator": int(group_a != group_b),
                "history_calls": n, "history_unique_targets": len(history.targets),
                "history_regions": len(history.regions),
                "history_short_share": history.short / n if n else 0,
                "history_unanswered_share": history.unanswered / n if n else 0,
                "history_mean_duration": mean,
                "history_duration_std": max(0, history.squared / n - mean * mean) ** 0.5 if n else 0,
                "history_incoming": len(inbound.calls),
                "history_reciprocal_share": len(history.targets.keys() & inbound.targets.keys()) / max(1, len(history.targets)),
                "history_pair_calls": history.targets[b],
                "history_reverse_pair_calls": inbound.targets[b],
                "seconds_since_previous": seconds - history.calls[-1][0] if n else window_seconds,
                "imsi_number_count": imsi_count, "imsi_active_calls": active_count,
            }
            numeric[position] = [values[name] for name in NUMERIC_FEATURES]
        for _, position, a, b, imsi, duration, type_, c in batch:
            if scenario_history is not None:
                scenario_history.add(seconds, a, b, imsi, c, duration, timestamp.hour, type_)
            outgoing[a].add(seconds, b, duration)
            incoming[b].add(seconds, a, duration)
            if imsi:
                imsis[imsi].add(seconds, a, duration)
                if duration:
                    active[imsi].append(seconds + duration)
        processed += len(batch)
        if processed % 250000 < len(batch):
            logging.getLogger(__name__).info("Признаки: %s / %s", processed, len(work))
    result = pd.DataFrame(numeric, columns=NUMERIC_FEATURES)
    result["type"] = work.type.to_numpy()
    result["source_group"] = source_groups.to_numpy()
    result["destination_group"] = destination_groups.to_numpy()
    if scenario_values is not None:
        result = pd.concat([result, pd.DataFrame(scenario_values, columns=SCENARIO_FEATURES)], axis=1)
    return result[FEATURE_COLUMNS if version == 2 else V1_FEATURE_COLUMNS]
