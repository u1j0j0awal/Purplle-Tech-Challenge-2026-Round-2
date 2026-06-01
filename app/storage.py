from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from app.models import StoreEvent


class EventStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("STORE_INTEL_EVENT_PATH", "data/events.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._events: dict[str, StoreEvent] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = StoreEvent.model_validate_json(line)
            self._events[event.event_id] = event

    def all(self) -> list[StoreEvent]:
        return sorted(self._events.values(), key=lambda e: e.timestamp)

    def add_many(self, events: list[StoreEvent]) -> tuple[int, int]:
        accepted = 0
        duplicates = 0
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                for event in events:
                    if event.event_id in self._events:
                        duplicates += 1
                        continue
                    self._events[event.event_id] = event
                    handle.write(event.model_dump_json() + "\n")
                    accepted += 1
        return accepted, duplicates

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self.path.write_text("", encoding="utf-8")


def load_json(path: str | None, default: dict) -> dict:
    if not path:
        return default
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))
