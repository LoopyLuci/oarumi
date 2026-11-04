"""AuditLog: append, replay, rotation, thread safety."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from oarumi.reliability.audit_log import AuditEvent, AuditLog


def test_append_and_replay(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.log_simple("pivot", "hello", value=1)
    log.log_simple("pivot", "world", value=2)
    events = log.replay()
    assert [e.event for e in events] == ["hello", "world"]
    assert events[0].payload == {"value": 1}


def test_rotation(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl", max_bytes=200)
    for i in range(20):
        log.log_simple("x", "e", i=i)
    rotated = list(tmp_path.glob("audit.jsonl.*"))
    assert rotated, "expected at least one rotated file"


def test_threaded_append(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")

    def writer(n: int) -> None:
        for _ in range(50):
            log.log_simple("x", "e", n=n)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    events = log.replay()
    assert len(events) == 200


def test_round_trip_event(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    ev = AuditEvent.make("x", "e", {"a": 1})
    log.log(ev)
    raw = (tmp_path / "audit.jsonl").read_text().strip()
    data = json.loads(raw)
    assert data["component"] == "x"
    assert data["payload"] == {"a": 1}
