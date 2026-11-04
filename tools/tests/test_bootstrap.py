"""Bootstrap: status reporting, readiness, install no-ops with placeholder URLs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from desktop import bootstrap


def _write_manifest(path: Path, assets: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps({"version": "0.1.0", "assets": assets}, indent=2))


def test_repo_manifest_is_ready_with_placeholder_urls() -> None:
    """With the shipped manifest (all optional), bootstrap reports ready."""
    boot = bootstrap.Bootstrap()
    statuses = boot.status()
    assert statuses, "expected assets in manifest"
    assert boot.is_ready() is True


def test_check_returns_zero_on_repo_manifest(capsys: pytest.CaptureFixture[str]) -> None:
    rc = bootstrap.main(["--check", "--json"])
    out, _ = capsys.readouterr()
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert all("id" in row for row in data)


def test_missing_required_asset_blocks_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "m.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "required-pack",
                "kind": "argos-pack",
                "url": "https://example.invalid/x",
                "sha256": "",
                "optional": False,
            }
        ],
    )
    boot = bootstrap.Bootstrap(manifest_path=manifest, dest=tmp_path / "out")
    assert boot.is_ready() is False


def test_install_skips_placeholder_urls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.json"
    _write_manifest(
        manifest,
        [
            {
                "id": "argos-es-en",
                "kind": "argos-pack",
                "url": "https://example.invalid/argos/es-en.argosmodel",
                "sha256": "",
                "optional": True,
            }
        ],
    )
    boot = bootstrap.Bootstrap(manifest_path=manifest, dest=tmp_path / "out")
    rc = boot.install()
    out, _ = capsys.readouterr()
    assert rc == 0
    assert "SKIP" in out


def test_offline_refuses_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "m.json"
    _write_manifest(manifest, [])
    boot = bootstrap.Bootstrap(manifest_path=manifest, dest=tmp_path / "out", offline=True)
    assert boot.install() == 2
