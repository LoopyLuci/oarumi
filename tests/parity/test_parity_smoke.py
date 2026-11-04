"""Smoke test: the parity runner replays the frozen parity-basic corpus with no failures."""

from __future__ import annotations

from pathlib import Path

from tools import parity_runner

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runner_replays_frozen_corpus() -> None:
    result = parity_runner.run(
        "parity-basic", db_path=REPO_ROOT / "language" / "oarumi.db", target="python", strict=True
    )
    assert result["total"] >= 200
    assert result["failed"] == 0
