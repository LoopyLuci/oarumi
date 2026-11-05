"""Display names: the GUI shows full names and never the raw engine codes."""

from __future__ import annotations

import pytest

from desktop.languages import language_name, modality_name, mood_name


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("zh", "Mandarin Chinese"),
        ("ar", "Arabic"),
    ],
)
def test_language_names_are_spelled_out(code: str, name: str) -> None:
    assert language_name(code) == name


def test_unknown_language_code_is_returned_unchanged() -> None:
    assert language_name("xx") == "xx"


@pytest.mark.parametrize(
    ("code", "label"),
    [("spoken", "Spoken"), ("signed", "Signed"), ("tactile", "Tactile")],
)
def test_modality_labels_are_capitalised(code: str, label: str) -> None:
    assert modality_name(code) == label


def test_mood_labels_replace_engine_codes() -> None:
    assert mood_name("DECL") == "Declarative"
    assert mood_name("INTERR") == "Interrogative"
    assert mood_name("UNKNOWN") == "Unknown"
