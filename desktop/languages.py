"""Display names for the codes the GUI stores internally.

The engine works with short codes ("es", "spoken", "DECL"). Views show the
names below and keep the code as item data, so a user never reads "es".
"""

from __future__ import annotations

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Mandarin Chinese",
    "ar": "Arabic",
}

_MODALITY_NAMES: dict[str, str] = {
    "spoken": "Spoken",
    "signed": "Signed",
    "tactile": "Tactile",
}

_MOOD_NAMES: dict[str, str] = {
    "DECL": "Declarative",
    "INTERR": "Interrogative",
    "IMPER": "Imperative",
    "PROM": "Promissive",
    "EXPRESS": "Expressive",
    "VOC": "Vocative",
}


def language_name(code: str) -> str:
    """Full English name for a language code. Unknown codes are returned unchanged."""
    return _LANGUAGE_NAMES.get(code, code)


def modality_name(code: str) -> str:
    """Capitalised label for a target modality code."""
    return _MODALITY_NAMES.get(code, code.capitalize())


def mood_name(code: str) -> str:
    """Grammatical mood label for an NSM mood code such as ``DECL``."""
    return _MOOD_NAMES.get(code, code.capitalize())
