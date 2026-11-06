"""Word segmentation shared by the spell checker and the language detector.

A word is a run of letters and combining marks. Digits, punctuation and
whitespace separate words. Words are lowercased character by character so
that offsets refer to the original text. The Kotlin port in
engine/kotlin/src/main/kotlin/oarumi/lang/Text.kt follows the same rules.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_MARK_CATEGORIES = frozenset({"Mn", "Mc"})


@dataclass(frozen=True, slots=True)
class Word:
    start: int
    end: int
    text: str


def is_word_char(ch: str) -> bool:
    return ch.isalpha() or unicodedata.category(ch) in _MARK_CATEGORIES


def split_words(text: str) -> list[Word]:
    """Return every word in `text` with its character span, lowercased."""
    words: list[Word] = []
    start: int | None = None
    for index, ch in enumerate(text):
        if is_word_char(ch):
            if start is None:
                start = index
        elif start is not None:
            words.append(Word(start, index, _lower(text[start:index])))
            start = None
    if start is not None:
        words.append(Word(start, len(text), _lower(text[start:])))
    return words


def _lower(run: str) -> str:
    return "".join(ch.lower() for ch in run)
