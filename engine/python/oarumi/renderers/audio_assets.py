"""Bundled click and hum audio assets, verified against a signed manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from oarumi.errors import IntegrityError


@dataclass(slots=True, frozen=True)
class AudioAsset:
    id: str
    path: Path
    sha256: str
    sample_rate: int


class AudioAssetLibrary:
    """Loads assets/audio/manifest.json and verifies each file's hash.

    An empty `sha256` in the manifest means "unverified" — permitted only when
    OARUMI_DEV_MODELS=1, so a fresh checkout can run tests before the generator
    has been invoked.
    """

    def __init__(self, root: Path, *, require_verified: bool = False) -> None:
        self._root = root
        manifest_path = root / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"audio manifest missing: {manifest_path}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._sample_rate = int(data.get("sample_rate", 22050))
        self._assets: dict[str, AudioAsset] = {}
        for entry in data.get("assets", []):
            asset = AudioAsset(
                id=str(entry["id"]),
                path=root / str(entry["path"]),
                sha256=str(entry.get("sha256") or ""),
                sample_rate=int(entry.get("sample_rate", self._sample_rate)),
            )
            if require_verified and not asset.sha256:
                raise IntegrityError(
                    f"asset {asset.id} has no sha256; run tools/generate_audio_assets.py"
                )
            if not asset.path.exists():
                raise FileNotFoundError(f"audio asset missing: {asset.path}")
            if asset.sha256:
                digest = hashlib.sha256(asset.path.read_bytes()).hexdigest()
                if digest != asset.sha256:
                    raise IntegrityError(
                        f"asset {asset.id} hash mismatch: {digest} != {asset.sha256}"
                    )
            self._assets[asset.id] = asset

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def get(self, asset_id: str) -> AudioAsset:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"no audio asset {asset_id!r}") from exc

    def has(self, asset_id: str) -> bool:
        return asset_id in self._assets

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._assets))
