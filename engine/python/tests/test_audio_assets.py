"""Audio asset integrity: manifest loading, hash verification, corruption detection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from oarumi.errors import IntegrityError
from oarumi.renderers.audio_assets import AudioAssetLibrary

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def generated_assets(tmp_path: Path) -> Path:
    dest = tmp_path / "audio"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_audio_assets.py"), "--dest", str(dest)],
        check=True,
        capture_output=True,
    )
    return dest


def test_manifest_has_19_assets(generated_assets: Path) -> None:
    lib = AudioAssetLibrary(generated_assets, require_verified=True)
    assert len(lib.ids()) == 19


def test_all_hashes_verify(generated_assets: Path) -> None:
    lib = AudioAssetLibrary(generated_assets, require_verified=True)
    for asset_id in lib.ids():
        assert lib.has(asset_id)


def test_corrupted_asset_raises(generated_assets: Path) -> None:
    target = generated_assets / "clicks" / "click_bilabial_plain.wav"
    target.write_bytes(b"not a wav")
    with pytest.raises(IntegrityError):
        AudioAssetLibrary(generated_assets, require_verified=True)


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        AudioAssetLibrary(tmp_path)


def test_unverified_manifest_allowed_when_not_required(tmp_path: Path) -> None:
    manifest = {
        "version": "0.1.0",
        "sample_rate": 22050,
        "assets": [{"id": "hum_steady", "path": "hums/hum_steady.wav", "sha256": ""}],
    }
    (tmp_path / "hums").mkdir()
    (tmp_path / "hums" / "hum_steady.wav").write_bytes(b"RIFF")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    lib = AudioAssetLibrary(tmp_path, require_verified=False)
    assert lib.has("hum_steady")
