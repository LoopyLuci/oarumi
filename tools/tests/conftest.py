"""Fixtures for tools/ tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(autouse=True)
def _force_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every tool test runs offline by default. Override explicitly if needed."""
    monkeypatch.setenv("OARUMI_OFFLINE", "1")
    monkeypatch.setenv("OARUMI_HOME", str(REPO_ROOT))


@pytest.fixture()
def audio_assets(repo_root: Path) -> Path:
    dest = repo_root / "assets" / "audio"
    if not (dest / "manifest.json").exists():
        pytest.skip("audio assets not generated; run tools/generate_audio_assets.py")
    return dest


@pytest.fixture()
def language_db(repo_root: Path) -> Path:
    db = repo_root / "language" / "oarumi.db"
    if not db.exists():
        pytest.skip("language DB missing; run ./scripts/bootstrap.sh")
    return db
