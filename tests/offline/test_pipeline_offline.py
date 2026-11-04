"""Full pipeline runs with zero network access."""

from __future__ import annotations

import pytest
from oarumi.pivot import phrasebook
from oarumi.types import TranslationRequest


def test_all_phrasebook_languages_offline(engine_pipeline) -> None:
    for lang in phrasebook.supported_languages():
        sample = list(phrasebook._PHRASEBOOK[lang].keys())[:2]
        for text in sample:
            result = engine_pipeline.translate(
                TranslationRequest(text=text, lang=lang, modality="spoken")
            )
            assert result.pivot["text"], f"{lang}:{text!r} produced empty pivot"


def test_all_modalities_offline(engine_pipeline) -> None:
    for modality in ["spoken", "signed", "tactile"]:
        result = engine_pipeline.translate(
            TranslationRequest(text="hola", lang="es", modality=modality)
        )
        assert modality in result.modalities or result.degraded


def test_tts_asset_backend_offline(engine_pipeline) -> None:
    result = engine_pipeline.translate(
        TranslationRequest(text="hola", lang="es", modality="spoken")
    )
    spoken = result.modalities.get("spoken")
    if spoken is None:
        pytest.skip("spoken not rendered in this environment")
    assert spoken["backend"] == "asset"
