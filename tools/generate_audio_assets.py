"""Generate the click and hum WAV assets and rewrite manifest.json with hashes.

Deterministic: the same inputs always produce the same bytes. Run this once
after cloning, and again whenever the asset catalogue changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = ROOT / "assets" / "audio"
SAMPLE_RATE = 22050

CLICKS = {
    "bilabial": 200,
    "dental": 400,
    "alveolar": 800,
    "lateral": 1200,
    "palatal": 1600,
}
ACCOMPANIMENTS = {
    "plain": {"mod": 0.0, "noise": 0.0},
    "nasal": {"mod": 50.0, "noise": 0.0},
    "aspirated": {"mod": 0.0, "noise": 0.35},
}
HUMS = {
    "steady": ("steady", 120.0, 120.0),
    "pulsed": ("pulsed", 120.0, 120.0),
    "rising": ("rising", 100.0, 150.0),
    "falling": ("falling", 150.0, 100.0),
}


def _write_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def _click_samples(freq: float, mod: float, noise: float) -> list[int]:
    n = int(SAMPLE_RATE * 0.06)
    out: list[int] = []
    rng = 12345
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 60.0)
        carrier = math.sin(2 * math.pi * freq * t)
        if mod:
            carrier *= 0.6 + 0.4 * math.sin(2 * math.pi * mod * t)
        if noise:
            rng = (1103515245 * rng + 12345) & 0x7FFFFFFF
            carrier += noise * ((rng / 0x7FFFFFFF) * 2 - 1)
        out.append(int(9000 * env * carrier))
    return out


def _hum_samples(shape: str, f0: float, f1: float) -> list[int]:
    n = int(SAMPLE_RATE * 0.5)
    out: list[int] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = f0 + (f1 - f0) * (i / n)
        env = 0.5 - 0.5 * math.cos(2 * math.pi * t * 2)
        amp = 0.6
        if shape == "pulsed":
            amp *= 0.5 + 0.5 * math.sin(2 * math.pi * 5.0 * t)
        out.append(int(9000 * amp * env * math.sin(2 * math.pi * freq * t)))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default=str(DEFAULT_DEST))
    args = parser.parse_args(argv)
    dest = Path(args.dest)

    assets: list[dict[str, object]] = []
    for place, freq in CLICKS.items():
        for acc, spec in ACCOMPANIMENTS.items():
            asset_id = f"click_{place}_{acc}"
            rel = f"clicks/{asset_id}.wav"
            path = dest / rel
            _write_wav(path, _click_samples(freq, spec["mod"], spec["noise"]))
            assets.append(_entry(asset_id, rel, path))

    for name, (shape, f0, f1) in HUMS.items():
        asset_id = f"hum_{name}"
        rel = f"hums/{asset_id}.wav"
        path = dest / rel
        _write_wav(path, _hum_samples(shape, f0, f1))
        assets.append(_entry(asset_id, rel, path))

    manifest = {
        "version": "0.1.0",
        "sample_rate": SAMPLE_RATE,
        "generated_by": "tools/generate_audio_assets.py",
        "assets": assets,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"OK   wrote {len(assets)} assets + manifest to {dest}")
    return 0


def _entry(asset_id: str, rel: str, path: Path) -> dict[str, object]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "id": asset_id,
        "path": rel,
        "sha256": digest,
        "sample_rate": SAMPLE_RATE,
    }


if __name__ == "__main__":
    raise SystemExit(main())
