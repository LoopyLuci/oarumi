"""Pivot translator parity: phrasebook hits, fallback events, trace paths."""

from __future__ import annotations

import pytest
from oarumi.pivot import phrasebook
from oarumi.pivot.translator import PivotTranslator


def test_phrasebook_complete(engine_db, parity_config: dict) -> None:
    """Every (lang, text) in the phrasebook is reachable and returns its target."""
    translator = PivotTranslator(cfg=_cfg())
    for lang in phrasebook.supported_languages():
        for text, expected in _all_phrases(lang):
            r = translator.translate(text, lang, "en")
            assert r.text == expected, f"{lang}:{text!r} -> {r.text!r} != {expected!r}"
            assert r.source == "phrasebook"


def test_unsupported_lang_raises() -> None:
    from oarumi.errors import FallbackRequired

    translator = PivotTranslator(cfg=_cfg())
    with pytest.raises(FallbackRequired):
        translator.translate("unknown phrase", "xx", "en")


def test_same_lang_passthrough() -> None:
    translator = PivotTranslator(cfg=_cfg())
    r = translator.translate("hello", "en", "en")
    assert r.text == "hello"
    assert r.source == "passthrough"


def _cfg():
    from oarumi.config import EngineConfig

    return EngineConfig.from_env()


def _all_phrases(lang: str):
    # Reach into the phrasebook's private table for the completeness test only.
    from oarumi.pivot.phrasebook import _PHRASEBOOK

    return list(_PHRASEBOOK[lang].items())
