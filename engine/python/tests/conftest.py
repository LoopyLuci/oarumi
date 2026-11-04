"""Fixtures for engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from oarumi.config import EngineConfig
from oarumi.db import LanguageDb


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def db(repo_root: Path) -> LanguageDb:
    path = repo_root / "language" / "oarumi.db"
    if not path.exists():
        pytest.skip(f"run ./scripts/bootstrap.sh first ({path} missing)")
    return LanguageDb(path)


@pytest.fixture()
def cfg(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> EngineConfig:
    monkeypatch.setenv("OARUMI_HOME", str(repo_root))
    monkeypatch.setenv("OARUMI_OFFLINE", "1")  # tests must be offline
    return EngineConfig.from_env()
