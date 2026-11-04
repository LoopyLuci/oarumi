"""Dev stub fetching: hashes, idempotency, hash regeneration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools import fetch_dev_stubs


def _write_manifest(path: Path, stubs: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"version": "0.1.0", "stubs": stubs}, indent=2))


def test_generates_and_verifies(tmp_path: Path) -> None:
    content = '{"kind":"stub"}'
    digest = hashlib.sha256(content.encode()).hexdigest()
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "s1",
                "filename": "s1.stub",
                "sha256": digest,
                "content": content,
            }
        ],
    )
    dest = tmp_path / "out"

    rc = fetch_dev_stubs.fetch(manifest, dest)
    assert rc == 0
    assert (dest / "s1.stub").read_text() == content

    rc = fetch_dev_stubs.fetch(manifest, dest, verify_only=True)
    assert rc == 0


def test_idempotent_skip(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    content = '{"kind":"stub"}'
    digest = hashlib.sha256(content.encode()).hexdigest()
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "s1",
                "filename": "s1.stub",
                "sha256": digest,
                "content": content,
            }
        ],
    )
    dest = tmp_path / "out"
    fetch_dev_stubs.fetch(manifest, dest)
    capsys.readouterr()
    fetch_dev_stubs.fetch(manifest, dest)
    out, _ = capsys.readouterr()
    assert "SKIP" in out


def test_hash_mismatch_fails(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "s1",
                "filename": "s1.stub",
                "sha256": "0" * 64,
                "content": "real",
            }
        ],
    )
    rc = fetch_dev_stubs.fetch(manifest, tmp_path / "out")
    assert rc == 1


def test_regenerate_hashes(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "s1",
                "filename": "s1.stub",
                "sha256": "0" * 64,
                "content": "real",
            }
        ],
    )
    rc = fetch_dev_stubs.regenerate_hashes(manifest)
    assert rc == 0
    data = json.loads(manifest.read_text())
    digest = hashlib.sha256(b"real").hexdigest()
    assert data["stubs"][0]["sha256"] == digest


def test_missing_manifest_is_not_fatal(tmp_path: Path) -> None:
    rc = fetch_dev_stubs.fetch(tmp_path / "nope.json", tmp_path / "out")
    assert rc == 0
