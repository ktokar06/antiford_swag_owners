"""Конфигурация обучения, независимая от настроек API и БД."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainConfig:
    iterations: int = 600
    depth: int = 6
    learning_rate: float = 0.05
    random_seed: int = 42
    thread_count: int = 4
    test_fraction: float = 0.2
    validation_fraction: float = 0.2
    early_stopping_rounds: int = 60
    max_false_positive_rate: float = 0.01
    review_threshold: int = 40
    window_seconds: int = 3600

    def __post_init__(self):
        if not (0 < self.test_fraction < 1 and 0 < self.validation_fraction < 1
                and self.test_fraction + self.validation_fraction < 1):
            raise ValueError("Доли validation/test должны быть > 0, сумма < 1")
        if not 0 <= self.max_false_positive_rate < 1:
            raise ValueError("max_false_positive_rate должен быть в [0, 1)")
        if not 0 < self.review_threshold < 100:
            raise ValueError("review_threshold должен быть в (0, 100)")
        if not (self.iterations > 0 and 1 <= self.depth <= 12 and 0 < self.learning_rate <= 1
                and self.thread_count > 0 and self.window_seconds > 0 and self.early_stopping_rounds > 0):
            raise ValueError("Некорректные параметры CatBoost или временного окна")

    @classmethod
    def load(cls, path: str | Path | None = None):
        return cls(**json.loads(Path(path).read_text())) if path else cls()

    def to_dict(self):
        return asdict(self)
