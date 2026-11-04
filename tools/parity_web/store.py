"""SQLite-backed storage for parity runs.

A run has one or more targets (e.g. ["python", "kotlin"]). Each target stores
the full parity_runner report as JSON. Diffs are computed on demand by the API.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           TEXT PRIMARY KEY,
    corpus       TEXT NOT NULL,
    targets      TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    finished_at  TEXT,
    error        TEXT
);

CREATE TABLE IF NOT EXISTS run_targets (
    run_id        TEXT NOT NULL,
    target        TEXT NOT NULL,
    status        TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT,
    payload_json  TEXT,
    error         TEXT,
    PRIMARY KEY (run_id, target),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class RunStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- public API -----------------------------------------------------

    def create_run(self, corpus: str, targets: list[str]) -> str:
        if not targets:
            raise ValueError("targets must be non-empty")
        run_id = str(uuid.uuid4())
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (id, corpus, targets, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, corpus, json.dumps(targets), "pending", _now()),
            )
            for target in targets:
                conn.execute(
                    "INSERT INTO run_targets (run_id, target, status) VALUES (?, ?, ?)",
                    (run_id, target, "pending"),
                )
        return run_id

    def mark_running(self, run_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = ?, started_at = ? WHERE id = ?",
                ("running", _now(), run_id),
            )

    def mark_target_running(self, run_id: str, target: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE run_targets SET status = ?, started_at = ? "
                "WHERE run_id = ? AND target = ?",
                ("running", _now(), run_id, target),
            )

    def complete_target(
        self,
        run_id: str,
        target: str,
        *,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        status = "done" if error is None else "failed"
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE run_targets SET status = ?, finished_at = ?, "
                "payload_json = ?, error = ? WHERE run_id = ? AND target = ?",
                (
                    status,
                    _now(),
                    json.dumps(payload) if payload is not None else None,
                    error,
                    run_id,
                    target,
                ),
            )

    def finish_run(self, run_id: str, *, error: str | None = None) -> None:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT status, error FROM run_targets WHERE run_id = ?", (run_id,)
            ).fetchall()
            statuses = [r["status"] for r in rows]
            # Surface target-level failures on the run when the caller gives no error.
            target_errors = [f"{r['error']}" for r in rows if r["error"]]
            run_error = error if error is not None else ("; ".join(target_errors) or None)
            if error is not None or not statuses:
                final = "failed"
            elif all(s == "done" for s in statuses):
                final = "done"
            elif any(s == "failed" for s in statuses):
                final = "failed"
            else:
                final = "partial"
            conn.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                (final, _now(), run_error, run_id),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            run_row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if run_row is None:
                return None
            target_rows = conn.execute(
                "SELECT * FROM run_targets WHERE run_id = ? ORDER BY target",
                (run_id,),
            ).fetchall()
        return {
            "id": run_row["id"],
            "corpus": run_row["corpus"],
            "targets": json.loads(run_row["targets"]),
            "status": run_row["status"],
            "created_at": run_row["created_at"],
            "started_at": run_row["started_at"],
            "finished_at": run_row["finished_at"],
            "error": run_row["error"],
            "target_results": {
                t["target"]: {
                    "target": t["target"],
                    "status": t["status"],
                    "started_at": t["started_at"],
                    "finished_at": t["finished_at"],
                    "payload": (
                        json.loads(t["payload_json"]) if t["payload_json"] is not None else None
                    ),
                    "error": t["error"],
                }
                for t in target_rows
            },
        }

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "corpus": r["corpus"],
                "targets": json.loads(r["targets"]),
                "status": r["status"],
                "created_at": r["created_at"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "error": r["error"],
            }
            for r in rows
        ]
