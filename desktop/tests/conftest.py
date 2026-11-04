"""Desktop GUI tests run headless with a QApplication fixture."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Must be set before importing PySide6 anywhere.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OARUMI_DISABLE_AVATAR", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtWidgets import QApplication

from desktop.state import AppState

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


@pytest.fixture(scope="session")
def state(qapp: QApplication) -> AppState:
    db = REPO_ROOT / "language" / "oarumi.db"
    manifest = REPO_ROOT / "assets" / "audio" / "manifest.json"
    if not db.exists() or not manifest.exists():
        pytest.skip("run ./scripts/bootstrap.sh and tools/generate_audio_assets.py")
    return AppState.from_env(repo_root=REPO_ROOT)
