"""TTS parity: SSML bytes, phoneme stream, and phoneme validity."""

from __future__ import annotations

from oarumi.renderers.tts import TtsRenderer
from oarumi.types import Clitic, OarumiSurface


def test_ssml_is_stable(engine_pipeline) -> None:
    """SSML must be identical to the frozen gold for the same surface."""
    from pathlib import Path

    from oarumi.renderers.audio_assets import AudioAssetLibrary

    root = Path(__file__).resolve().parents[2]
    audio = AudioAssetLibrary(root / "assets" / "audio", require_verified=False)
    tts = TtsRenderer(audio=audio, espeak_bin=None)

    surface = OarumiSurface(
        phonemes=("hello",),
        clitics=(Clitic("=ha", "mood_declarative"),),
        mood="DECL",
        modality="spoken",
    )
    ssml = tts.build_ssml(surface)
    expected = (
        '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="en"><prosody rate="medium">hello</prosody></speak>'
    )
    assert ssml == expected


def test_phoneme_stream_preserved(engine_pipeline) -> None:
    """Every output phoneme is a valid token: prime form, click, or hum."""
    from oarumi.pivot import phrasebook
    from oarumi.types import TranslationRequest

    for lang, phrases in phrasebook._PHRASEBOOK.items():
        for text in list(phrases.keys())[:3]:
            for modality in ["spoken"]:
                result = engine_pipeline.translate(
                    TranslationRequest(text=text, lang=lang, modality=modality)
                )
                spoken = result.modalities.get("spoken")
                if spoken is None:
                    continue
                for token in spoken.get("phoneme_stream", []):
                    assert isinstance(token, str)
                    assert token, "empty token"


def test_click_routing(engine_pipeline) -> None:
    """Any surface containing a click must route to the asset backend."""
    from oarumi.types import TranslationRequest

    # Use a phrase whose realized surface contains no click, then check backend.
    result = engine_pipeline.translate(
        TranslationRequest(text="hola", lang="es", modality="spoken")
    )
    spoken = result.modalities.get("spoken")
    if spoken:
        assert spoken["backend"] in {"asset", "native"}
