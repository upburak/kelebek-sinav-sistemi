"""Karar 58: çalışan dağıtımın aşama, süre ve en iyi çözüm bilgisini paylaş; durdurma isteğini taşı."""

import threading
import time

STEPS = (
    ("prepare", "Öğrenci, derslik ve kurallar hazırlanıyor"),
    ("model", "Komşuluk kuralları ve kapasite modeli kuruluyor"),
    ("search", "En dengeli yerleşim aranıyor"),
    ("save", "Aday kaydediliyor"),
)
_registry: dict[str, "DistributionProgress"] = {}
_guard = threading.Lock()


class DistributionProgress:
    def __init__(self, organization_id: str, time_limit: float):
        self.organization_id = organization_id
        self.time_limit = time_limit
        self.started = time.monotonic()
        self.search_started: float | None = None
        self.stage = "prepare"
        self.solutions = 0
        self.best_affected: int | None = None
        self.best_objective: int | None = None
        self.stop_event = threading.Event()
        self.finished = False
        self.ended: float | None = None
        self.outcome: str | None = None

    def set_stage(self, stage: str) -> None:
        self.stage = stage
        if stage == "search":
            self.search_started = time.monotonic()

    def record_solution(self, objective: float, affected: int) -> None:
        self.solutions += 1
        self.best_objective = int(objective)
        self.best_affected = affected

    def snapshot(self) -> dict:
        now = self.ended or time.monotonic()
        searching = self.search_started is not None and self.stage == "search"
        remaining = max(0.0, self.time_limit - (now - self.search_started)) if searching else None
        return {
            "active": not self.finished, "stage": self.stage,
            "steps": [{"key": key, "label": label} for key, label in STEPS],
            "elapsed_seconds": round(now - self.started, 1),
            "remaining_max_seconds": round(remaining, 1) if remaining is not None else None,
            "time_limit_seconds": self.time_limit, "solutions_found": self.solutions,
            "best_affected_student_count": self.best_affected, "best_objective": self.best_objective,
            "stop_requested": self.stop_event.is_set(), "outcome": self.outcome,
        }


def start(organization_id: str, time_limit: float) -> DistributionProgress:
    progress = DistributionProgress(organization_id, time_limit)
    with _guard:
        _registry[organization_id] = progress
    return progress


def finish(progress: DistributionProgress, outcome: str) -> None:
    progress.ended = time.monotonic()
    progress.finished = True
    progress.outcome = outcome


def get(organization_id: str) -> DistributionProgress | None:
    with _guard:
        return _registry.get(organization_id)
