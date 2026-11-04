"""Append-only JSONL audit log. Thread-safe. Rotates at 10 MB."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class AuditEvent:
    component: str
    event: str
    payload: dict[str, Any]
    t: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "t": self.t,
            "component": self.component,
            "event": self.event,
            "payload": self.payload,
        }

    @classmethod
    def make(cls, component: str, event: str, payload: dict[str, Any]) -> AuditEvent:
        return cls(
            component=component,
            event=event,
            payload=payload,
            t=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )


class AuditLog:
    def __init__(self, path: Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._path = path
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def log(self, event: AuditEvent) -> None:
        line = json.dumps(event.to_json(), ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._rotate_if_needed(len(line) + 1)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def log_simple(self, component: str, event: str, **payload: Any) -> None:
        self.log(AuditEvent.make(component, event, dict(payload)))

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        if not self._path.exists():
            return
        try:
            size = self._path.stat().st_size
        except FileNotFoundError:
            return
        if size + incoming_bytes <= self._max_bytes:
            return
        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        rotated = self._path.with_name(f"{self._path.name}.{stamp}")
        n = 1
        while rotated.exists():  # two rotations in the same second must not collide
            rotated = self._path.with_name(f"{self._path.name}.{stamp}.{n}")
            n += 1
        self._path.rename(rotated)

    def replay(self) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        for rotated in sorted(self._path.parent.glob(f"{self._path.name}.*")):
            events.extend(self._read_file(rotated))
        events.extend(self._read_file(self._path))
        return events

    @staticmethod
    def _read_file(path: Path) -> list[AuditEvent]:
        if not path.exists():
            return []
        out: list[AuditEvent] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                out.append(
                    AuditEvent(
                        component=data["component"],
                        event=data["event"],
                        payload=data.get("payload", {}),
                        t=data["t"],
                        id=data.get("id", ""),
                    )
                )
        return out
