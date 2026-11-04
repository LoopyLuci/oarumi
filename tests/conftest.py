"""Shared pytest fixtures for the Oarumi test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "language" / "oarumi.db"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def db_path() -> Path:
    if not DB_PATH.exists():
        pytest.skip(f"language DB not seeded at {DB_PATH}; run ./scripts/bootstrap.sh")
    return DB_PATH


@pytest.fixture(autouse=True)
def _offline_guard(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Any test not marked `offline` still must not open sockets in CI."""
    if request.node.get_closest_marker("offline") is None:
        return
    if os.environ.get("OARUMI_OFFLINE") != "1":
        monkeypatch.setenv("OARUMI_OFFLINE", "1")


@pytest.fixture(scope="session")
def engine_db():
    from oarumi.db import LanguageDb

    db_path = ROOT / "language" / "oarumi.db"
    if not db_path.exists():
        pytest.skip(f"language DB missing: {db_path}; run ./scripts/bootstrap.sh")
    return LanguageDb(db_path)


@pytest.fixture(scope="session")
def engine_pipeline(engine_db):
    from tools.parity_setup import build_pipeline

    try:
        return build_pipeline(engine_db, ROOT)
    except FileNotFoundError as exc:
        pytest.skip(f"{exc}; run tools/generate_audio_assets.py")
