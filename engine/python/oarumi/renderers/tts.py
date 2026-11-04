"""Spoken renderer.

Two backends:

  - EspeakTtsBackend: uses the `espeak-ng` CLI. Supports partial SSML, IPA/
    X-SAMPA phoneme input, and a `clk` phoneme feature for clicks.
  - AssetTtsBackend: deterministic, dependency-free. Concatenates bundled
    click/hum WAVs and a procedurally generated tone per ordinary phoneme.
    Always produces a phoneme-valid WAV; intelligibility is intentionally low.

Routing rule: any surface that contains a click or a hum token uses the asset
backend (because eSpeak's SSML does not accept <audio>); otherwise the eSpeak
backend is tried first and the asset backend is the fallback.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oarumi.errors import CapabilityMissingError
from oarumi.renderers.audio_assets import AudioAssetLibrary
from oarumi.renderers.base import RenderOutput
from oarumi.types import OarumiSurface

CLICK_TOKENS: frozenset[str] = frozenset(
    {
        "ʘ",
        "ʘ̃",
        "ʘʰ",
        "ǀ",
        "ǀ̃",
        "ǀʰ",
        "ǃ",
        "ǃ̃",
        "ǃʰ",
        "ǁ",
        "ǁ̃",
        "ǁʰ",
        "ǂ",
        "ǂ̃",
        "ǂʰ",
    }
)

HUM_TOKENS: frozenset[str] = frozenset(
    {
        "hum_steady",
        "hum_pulsed",
        "hum_rising",
        "hum_falling",
    }
)

_CLICK_ASSET = {
    "ʘ": "click_bilabial_plain",
    "ʘ̃": "click_bilabial_nasal",
    "ʘʰ": "click_bilabial_aspirated",
    "ǀ": "click_dental_plain",
    "ǀ̃": "click_dental_nasal",
    "ǀʰ": "click_dental_aspirated",
    "ǃ": "click_alveolar_plain",
    "ǃ̃": "click_alveolar_nasal",
    "ǃʰ": "click_alveolar_aspirated",
    "ǁ": "click_lateral_plain",
    "ǁ̃": "click_lateral_nasal",
    "ǁʰ": "click_lateral_aspirated",
    "ǂ": "click_palatal_plain",
    "ǂ̃": "click_palatal_nasal",
    "ǂʰ": "click_palatal_aspirated",
}

_HUM_ASSET = {tok: tok for tok in HUM_TOKENS}


@dataclass(slots=True)
class TtsRenderer:
    audio: AudioAssetLibrary
    espeak_bin: str | None = None
    _tmpdir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="oarumi-tts-")))
    modality: str = "spoken"

    def __post_init__(self) -> None:
        if self.espeak_bin is None:
            self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")

    # --- public ---------------------------------------------------------

    def render(self, surface: OarumiSurface, **kwargs: Any) -> RenderOutput:
        stream = list(surface.phonemes)
        if not stream:
            return RenderOutput(
                modality=self.modality,
                payload={"phoneme_stream": [], "audio_path": None},
                valid=False,
                errors=("empty_phoneme_stream",),
            )

        has_special = any(t in CLICK_TOKENS or t in HUM_TOKENS for t in stream)
        backend = "asset"
        if not has_special and self.espeak_bin:
            backend = "espeak"

        out = self._tmpdir / f"utterance-{abs(hash(tuple(stream))) & 0xFFFFFFFF:08x}.wav"

        if backend == "espeak":
            try:
                ssml = self.build_ssml(surface)
                self._espeak_synthesize(ssml, out)
                return RenderOutput(
                    modality=self.modality,
                    payload={
                        "audio_path": str(out),
                        "ssml": ssml,
                        "phoneme_stream": stream,
                        "backend": "native",
                        "duration_ms": _wav_duration_ms(out),
                    },
                    valid=True,
                )
            except (CapabilityMissingError, subprocess.SubprocessError, OSError):
                backend = "asset"

        self._asset_synthesize(stream, out)
        return RenderOutput(
            modality=self.modality,
            payload={
                "audio_path": str(out),
                "ssml": None,
                "phoneme_stream": stream,
                "backend": "asset",
                "duration_ms": _wav_duration_ms(out),
            },
            valid=True,
        )

    # --- SSML -----------------------------------------------------------

    def build_ssml(self, surface: OarumiSurface) -> str:
        body = " ".join(surface.phonemes)
        rate = {
            "DECL": "medium",
            "INTERR": "medium",
            "IMPER": "fast",
            "PROM": "medium",
            "EXPRESS": "medium",
            "VOC": "slow",
        }.get(surface.mood, "medium")
        return (
            '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xml:lang="en">'
            f'<prosody rate="{rate}">{body}</prosody>'
            "</speak>"
        )

    def _espeak_synthesize(self, ssml: str, out: Path) -> None:
        assert self.espeak_bin is not None
        proc = subprocess.run(
            [self.espeak_bin, "-m", "-w", str(out)],
            input=ssml.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not out.exists():
            raise CapabilityMissingError(
                f"espeak failed: {proc.stderr.decode('utf-8', 'replace')[:200]}",
                capability="espeak",
            )

    # --- asset backend --------------------------------------------------

    def _asset_synthesize(self, stream: list[str], out: Path) -> None:
        frames: list[bytes] = []
        params: tuple[int, int, int] | None = None
        for token in stream:
            asset_id: str | None = None
            if token in CLICK_TOKENS:
                asset_id = _CLICK_ASSET[token]
            elif token in HUM_TOKENS:
                asset_id = _HUM_ASSET[token]
            if asset_id is not None:
                wav = self.audio.get(asset_id)
                p, chunk = _read_wav(wav.path)
                if params is None:
                    params = p
                frames.append(chunk)
            else:
                p, chunk = _tone_frames(token, self.audio.sample_rate)
                if params is None:
                    params = p
                frames.append(chunk)
        if params is None:
            params = (1, 2, self.audio.sample_rate)
        _write_wav(out, params, b"".join(frames))


@dataclass(slots=True)
class EspeakTtsBackend:
    """Thin wrapper kept for parity with the backend-name in RenderOutput."""

    bin: str

    def synthesize(self, ssml: str, out: Path) -> None:
        proc = subprocess.run(
            [self.bin, "-m", "-w", str(out)],
            input=ssml.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise CapabilityMissingError("espeak failed", capability="espeak")


@dataclass(slots=True)
class AssetTtsBackend:
    """Deterministic backend name holder; logic lives in TtsRenderer."""

    sample_rate: int = 22050


# --- WAV helpers --------------------------------------------------------


def _read_wav(path: Path) -> tuple[tuple[int, int, int], bytes]:
    with wave.open(str(path), "rb") as wf:
        params = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
        return params, wf.readframes(wf.getnframes())


def _tone_frames(token: str, sample_rate: int) -> tuple[tuple[int, int, int], bytes]:
    import math
    import struct

    duration_s = 0.09
    n = int(sample_rate * duration_s)
    freq = 180 + (sum(token.encode("utf-8")) % 220)
    buf = bytearray()
    for i in range(n):
        env = math.sin(math.pi * i / n)
        sample = int(12000 * env * math.sin(2 * math.pi * freq * i / sample_rate))
        buf.extend(struct.pack("<h", sample))
    return (1, 2, sample_rate), bytes(buf)


def _write_wav(path: Path, params: tuple[int, int, int], frames: bytes) -> None:
    channels, sampwidth, rate = params
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(frames)


def _wav_duration_ms(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as wf:
            return int(1000 * wf.getnframes() / wf.getframerate())
    except (wave.Error, OSError):
        return 0
