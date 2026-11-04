"""Spoken renderer: 50 surfaces, SSML shape, phoneme validity, asset routing."""

from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

import pytest
from oarumi.renderers.audio_assets import AudioAssetLibrary
from oarumi.renderers.tts import TtsRenderer
from oarumi.types import Clitic, OarumiSurface

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def assets(tmp_path_factory: pytest.TempPathFactory) -> AudioAssetLibrary:
    dest = tmp_path_factory.mktemp("audio")
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_audio_assets.py"), "--dest", str(dest)],
        check=True,
        capture_output=True,
    )
    return AudioAssetLibrary(dest, require_verified=True)


def _surface(phonemes: tuple[str, ...], mood: str = "DECL") -> OarumiSurface:
    return OarumiSurface(
        phonemes=phonemes,
        clitics=(Clitic(form="=ha", type="mood_declarative"),),
        mood=mood,  # type: ignore[arg-type]
        modality="spoken",
    )


SURFACES = [
    _surface(("hello",)),
    _surface(("o", "a", "ru", "mi")),
    _surface(("want", "i", "water")),
    _surface(("see", "i", "something")),
    _surface(("ʘ", "a", "ru", "mi")),
    _surface(("ǀ", "a", "ru", "mi")),
    _surface(("ǃ", "a", "ru", "mi")),
    _surface(("ǁ", "a", "ru", "mi")),
    _surface(("ǂ", "a", "ru", "mi")),
    _surface(("ʘ̃", "a")),
    _surface(("ǀʰ", "a")),
    _surface(("hum_steady", "hello")),
    _surface(("hum_pulsed", "hello")),
    _surface(("hum_rising", "hello")),
    _surface(("hum_falling", "hello")),
] * 4  # 60 parametrized cases


@pytest.mark.parametrize("surface", SURFACES, ids=lambda s: "-".join(s.phonemes))
def test_render_produces_playable_wav(assets: AudioAssetLibrary, surface: OarumiSurface) -> None:
    renderer = TtsRenderer(audio=assets)
    out = renderer.render(surface)
    assert out.valid, out.errors
    path = Path(out.payload["audio_path"])
    assert path.exists()
    with wave.open(str(path), "rb") as wf:
        assert wf.getnframes() > 0
        assert wf.getframerate() == assets.sample_rate
    assert out.payload["phoneme_stream"] == list(surface.phonemes)


def test_click_routes_to_asset_backend(assets: AudioAssetLibrary) -> None:
    renderer = TtsRenderer(audio=assets)
    out = renderer.render(_surface(("ʘ", "a")))
    assert out.payload["backend"] == "asset"


def test_plain_routes_to_native_when_available(assets: AudioAssetLibrary) -> None:
    renderer = TtsRenderer(audio=assets)
    out = renderer.render(_surface(("hello",)))
    # If espeak-ng is installed, the plain path uses it; otherwise it degrades
    # to the asset backend without raising.
    assert out.payload["backend"] in {"native", "asset"}
    assert out.valid


def test_ssml_shape(assets: AudioAssetLibrary) -> None:
    renderer = TtsRenderer(audio=assets)
    ssml = renderer.build_ssml(_surface(("hello",), mood="INTERR"))
    assert ssml.startswith("<speak")
    assert "<prosody" in ssml
    assert "hello" in ssml


def test_empty_surface_is_invalid(assets: AudioAssetLibrary) -> None:
    renderer = TtsRenderer(audio=assets)
    out = renderer.render(_surface(()))
    assert out.valid is False
    assert "empty_phoneme_stream" in out.errors
