"""Dictionary spell checker with edit-distance suggestions.

Suggestions are the known words within edit distance 1 of the input, or
distance 2 when there is none. Candidates are ranked by frequency, then by
spelling, so the same input always gives the same list. Kotlin port:
engine/kotlin/src/main/kotlin/oarumi/lang/SpellChecker.kt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from oarumi.lang.packs import LanguagePack
from oarumi.lang.text import split_words

_MAX_SECOND_PASS_LENGTH = 12


@dataclass(frozen=True, slots=True)
class Misspelling:
    start: int
    end: int
    word: str
    suggestions: tuple[str, ...]


class SpellChecker:
    def __init__(self, words: Mapping[str, int]) -> None:
        self._freq: dict[str, int] = dict(words)
        self._alphabet: tuple[str, ...] = tuple(sorted({ch for word in self._freq for ch in word}))

    @classmethod
    def from_pack(cls, pack: LanguagePack) -> SpellChecker:
        return cls(pack.words)

    @property
    def size(self) -> int:
        return len(self._freq)

    def is_known(self, word: str) -> bool:
        return word.lower() in self._freq

    def suggest(self, word: str, limit: int = 5) -> tuple[str, ...]:
        lowered = word.lower()
        if not lowered or lowered in self._freq:
            return ()
        first = self._edits1(lowered)
        found = self._rank(first)
        if not found and len(lowered) <= _MAX_SECOND_PASS_LENGTH:
            second: set[str] = set()
            for edit in first:
                second |= self._edits1(edit)
            found = self._rank(second)
        return tuple(found[:limit])

    def check(self, text: str, suggestions: int = 3) -> list[Misspelling]:
        """Return every unknown word in `text`, with suggestions for each."""
        problems: list[Misspelling] = []
        for word in split_words(text):
            if (
                len(word.text) < 2
                or word.text in self._freq
                or self._has_digit(text, word.start, word.end)
            ):
                continue
            problems.append(
                Misspelling(
                    start=word.start,
                    end=word.end,
                    word=text[word.start : word.end],
                    suggestions=self.suggest(word.text, suggestions),
                )
            )
        return problems

    def _rank(self, candidates: set[str]) -> list[str]:
        known = [word for word in candidates if word in self._freq]
        known.sort(key=lambda word: (-self._freq[word], word))
        return known

    def _edits1(self, word: str) -> set[str]:
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        edits: set[str] = set()
        for left, right in splits:
            if right:
                edits.add(left + right[1:])
                for ch in self._alphabet:
                    edits.add(left + ch + right[1:])
            if len(right) > 1:
                edits.add(left + right[1] + right[0] + right[2:])
            for ch in self._alphabet:
                edits.add(left + ch + right)
        edits.discard(word)
        return edits

    @staticmethod
    def _has_digit(text: str, start: int, end: int) -> bool:
        return any(ch.isdigit() for ch in text[start:end])
