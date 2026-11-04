"""Pivot translator, phrasebook, and no-network behavior."""

from __future__ import annotations

import pytest
from oarumi.config import EngineConfig
from oarumi.errors import FallbackRequired
from oarumi.pivot import phrasebook
from oarumi.pivot.translator import PivotTranslator


def test_phrasebook_hit(cfg: EngineConfig) -> None:
    t = PivotTranslator(cfg=cfg)
    r = t.translate("hola", "es", "en")
    assert r.text == "hello"
    assert r.source == "phrasebook"


def test_same_lang_passthrough(cfg: EngineConfig) -> None:
    t = PivotTranslator(cfg=cfg)
    r = t.translate("hello", "en", "en")
    assert r.source == "passthrough"


def test_no_path_raises_fallback(cfg: EngineConfig) -> None:
    t = PivotTranslator(cfg=cfg)
    with pytest.raises(FallbackRequired):
        t.translate("completely unknown phrase", "xx", "en")


def test_supported_languages_include_seed() -> None:
    langs = phrasebook.supported_languages()
    for lang in ("es", "fr", "de", "zh", "ar"):
        assert lang in langs
