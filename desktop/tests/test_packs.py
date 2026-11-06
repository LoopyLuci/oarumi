"""Pack manager: checksum-verified installs and language support from installed packs."""

from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path

import pytest
from oarumi.lang import PackError
from oarumi.lang.packs import PackEntry

from desktop.packs import PackManager

REPO_PACKS = Path(__file__).resolve().parents[2] / "language" / "packs"


def _extra_entry(manager: PackManager) -> PackEntry:
    return next(entry for entry in manager.entries() if entry.code == "pt")


def test_base_packs_are_available_without_installing(tmp_path: Path) -> None:
    manager = PackManager(bundled_dir=REPO_PACKS, installed_dir=tmp_path)
    es = next(entry for entry in manager.entries() if entry.code == "es")
    assert manager.is_installed(es)
    assert manager.spell_checker("es") is not None
    assert manager.spell_checker("zh") is None  # no spelling dictionary for Mandarin


def test_extra_pack_needs_a_download_before_it_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = PackManager(bundled_dir=REPO_PACKS, installed_dir=tmp_path)
    entry = _extra_entry(manager)
    assert not manager.is_installed(entry)
    assert manager.spell_checker("pt") is None

    blob = (REPO_PACKS / entry.file).read_bytes()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(blob))
    manager.download(entry)

    assert manager.is_installed(entry)
    assert manager.spell_checker("pt") is not None
    assert "pt" in manager.detector().languages


def test_download_is_refused_when_the_checksum_is_wrong(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = PackManager(bundled_dir=REPO_PACKS, installed_dir=tmp_path)
    entry = _extra_entry(manager)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(b"tampered"))
    with pytest.raises(PackError):
        manager.download(entry)
    assert not manager.is_installed(entry)
    assert not list(tmp_path.glob("*.partial"))


def test_removing_an_extra_pack_drops_its_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = PackManager(bundled_dir=REPO_PACKS, installed_dir=tmp_path)
    entry = _extra_entry(manager)
    blob = (REPO_PACKS / entry.file).read_bytes()
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(blob))
    manager.download(entry)
    manager.remove(entry)
    assert not manager.is_installed(entry)
    assert manager.spell_checker("pt") is None


def test_index_digest_matches_the_shipped_file() -> None:
    manager = PackManager(bundled_dir=REPO_PACKS, installed_dir=REPO_PACKS / "__none__")
    for entry in manager.entries():
        assert hashlib.sha256((REPO_PACKS / entry.file).read_bytes()).hexdigest() == entry.sha256
