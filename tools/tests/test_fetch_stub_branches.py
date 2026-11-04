"""fetch_dev_stubs branches the main suite does not reach. No network is used."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tools import fetch_dev_stubs


def _manifest(path: Path, stubs: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps({"stubs": stubs}), encoding="utf-8")
    return path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_verify_reports_missing_and_mismatched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "bad.json").write_text("different", encoding="utf-8")
    manifest = _manifest(
        tmp_path / "m.json",
        [
            {"filename": "missing.json", "content": "x", "sha256": _sha("x")},
            {"filename": "bad.json", "content": "y", "sha256": _sha("y")},
        ],
    )
    assert fetch_dev_stubs.fetch(manifest, dest, verify_only=True) == 1
    err = capsys.readouterr().err
    assert "MISS missing.json" in err
    assert "FAIL bad.json" in err


def test_verify_passes_when_hashes_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "ok.json").write_text("fine", encoding="utf-8")
    manifest = _manifest(
        tmp_path / "m.json",
        [{"filename": "ok.json", "content": "fine", "sha256": _sha("fine")}],
    )
    assert fetch_dev_stubs.fetch(manifest, dest, verify_only=True) == 0
    assert "OK   ok.json" in capsys.readouterr().out


def test_offline_skips_url_downloads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = _manifest(
        tmp_path / "m.json",
        [{"filename": "remote.bin", "url": "https://example.invalid/x", "sha256": _sha("")}],
    )
    assert fetch_dev_stubs.fetch(manifest, tmp_path / "dest", offline=True) == 0
    assert "offline, skipping download" in capsys.readouterr().err


def test_url_entry_is_downloaded_and_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_download(url: str, target: Path, timeout_s: float = 30.0) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"payload")

    monkeypatch.setattr(fetch_dev_stubs, "_download", fake_download)
    manifest = _manifest(
        tmp_path / "m.json",
        [{"filename": "remote.bin", "url": "https://example.invalid/x", "sha256": _sha("payload")}],
    )
    assert fetch_dev_stubs.fetch(manifest, tmp_path / "dest") == 0
    assert "OK   remote.bin" in capsys.readouterr().out


def test_download_error_is_counted_as_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(url: str, target: Path, timeout_s: float = 30.0) -> None:
        raise OSError("network down")

    monkeypatch.setattr(fetch_dev_stubs, "_download", boom)
    manifest = _manifest(
        tmp_path / "m.json",
        [{"filename": "remote.bin", "url": "https://example.invalid/x", "sha256": _sha("")}],
    )
    assert fetch_dev_stubs.fetch(manifest, tmp_path / "dest") == 1
    assert "FAIL remote.bin: network down" in capsys.readouterr().err


def test_entry_without_content_or_url_is_warned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = _manifest(tmp_path / "m.json", [{"filename": "empty.bin", "sha256": _sha("")}])
    assert fetch_dev_stubs.fetch(manifest, tmp_path / "dest") == 0
    assert "no content or url" in capsys.readouterr().err


def test_download_writes_partial_then_renames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"bytes"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResponse())
    target = tmp_path / "nested" / "stub.bin"
    fetch_dev_stubs._download("https://example.invalid/x", target)
    assert target.read_bytes() == b"bytes"
    assert not target.with_suffix(".bin.partial").exists()


def test_main_regenerates_and_fetches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = _manifest(
        tmp_path / "m.json",
        [{"filename": "a.json", "content": "hi", "sha256": "stale"}],
    )
    assert fetch_dev_stubs.main(["--manifest", str(manifest), "--regenerate-hashes"]) == 0
    assert "updated 1 hash(es)" in capsys.readouterr().out

    dest = tmp_path / "dest"
    assert fetch_dev_stubs.main(["--manifest", str(manifest), "--dest", str(dest)]) == 0
    assert (dest / "a.json").read_text(encoding="utf-8") == "hi"
