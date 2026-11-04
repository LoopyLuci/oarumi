"""End-to-end pipeline over the phrasebook corpus."""

from __future__ import annotations

import pytest
from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.pipeline import Pipeline
from oarumi.types import TranslationRequest

LANGS_AND_INPUTS = [
    ("es", "hola"),
    ("es", "quiero agua"),
    ("es", "yo veo el libro"),
    ("fr", "bonjour"),
    ("de", "hallo"),
    ("zh", "你好"),
]


@pytest.mark.parametrize(("lang", "text"), LANGS_AND_INPUTS)
def test_translate_returns_full_result(
    db: LanguageDb, cfg: EngineConfig, lang: str, text: str
) -> None:
    pipeline = Pipeline(db=db, cfg=cfg)
    result = pipeline.translate(TranslationRequest(text=text, lang=lang))
    j = result.to_json()
    for key in (
        "request_id",
        "input",
        "pivot",
        "nsm",
        "surface",
        "modalities",
        "trace",
        "failover_events",
        "degraded",
    ):
        assert key in j
    assert j["nsm"]["valid"] is True
    assert j["surface"]["phonemes"]


def test_unknown_language_degrades_not_crashes(db: LanguageDb, cfg: EngineConfig) -> None:
    pipeline = Pipeline(db=db, cfg=cfg)
    result = pipeline.translate(TranslationRequest(text="xyzzy", lang="xx"))
    assert result.degraded is True
    assert result.failover_events
