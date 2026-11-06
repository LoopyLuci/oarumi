"""Character n-gram language detection over the installed language packs.

Each pack's n-gram counts become a probability table. A text is scored by its
log-likelihood under every installed table. An n-gram that a profile does not
keep is charged half that profile's smallest stored probability, so a pruned
profile is not punished harder than a full one. The best table wins if it
beats the runner-up by at least MIN_MARGIN nats. Otherwise the detector
reports no answer, and the caller keeps the language the user chose.

The model is deterministic and needs no network. Kotlin port:
engine/kotlin/src/main/kotlin/oarumi/lang/LanguageDetector.kt.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from oarumi.lang.text import split_words

MIN_MARGIN = 2.0
WORD_BONUS = 8.0


@dataclass(frozen=True, slots=True)
class Detection:
    code: str | None
    confidence: float
    ranking: tuple[tuple[str, float], ...]


def fold(ch: str) -> str:
    """Collapse syllable blocks onto one representative, as langdetect's profiles expect."""
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return "가"
    if 0x3040 <= code <= 0x309F:
        return "あ"
    if 0x30A0 <= code <= 0x30FF:
        return "ア"
    return ch


def ngrams(text: str) -> dict[str, int]:
    """Count 1- to 3-grams inside each word, padded with a space on both sides."""
    counts: dict[str, int] = {}
    for word in split_words(text):
        padded = " " + "".join(fold(ch) for ch in word.text) + " "
        for size in (1, 2, 3):
            for index in range(len(padded) - size + 1):
                gram = padded[index : index + size]
                if size == 1 and gram == " ":
                    continue
                counts[gram] = counts.get(gram, 0) + 1
    return counts


class LanguageDetector:
    def __init__(
        self,
        profiles: Mapping[str, Mapping[str, int]],
        dictionaries: Mapping[str, Mapping[str, int]] | None = None,
    ) -> None:
        self._dictionaries: dict[str, Mapping[str, int]] = dict(dictionaries or {})
        self._models: dict[str, tuple[dict[str, float], float]] = {}
        for code in sorted(profiles):
            counts = profiles[code]
            total = sum(counts.values())
            if total <= 0:
                continue
            probabilities = {gram: count / total for gram, count in sorted(counts.items())}
            floor = 0.5 * min(probabilities.values())
            self._models[code] = (probabilities, floor)

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(self._models)

    def detect(self, text: str) -> Detection:
        grams = ngrams(text)
        if not grams or len(self._models) < 2:
            return Detection(code=None, confidence=0.0, ranking=())
        words = [word.text for word in split_words(text)]

        scores: list[tuple[str, float]] = []
        for code, (probabilities, floor) in self._models.items():
            total = 0.0
            for gram, count in sorted(grams.items()):
                total += count * math.log(probabilities.get(gram, floor))
            dictionary = self._dictionaries.get(code)
            if dictionary is not None:
                total += WORD_BONUS * sum(1 for word in words if word in dictionary)
            scores.append((code, total))
        scores.sort(key=lambda item: (-item[1], item[0]))

        best_code, best = scores[0]
        runner_up = scores[1][1]
        share = 1.0 / sum(math.exp(score - best) for _, score in scores)
        decided = best_code if best - runner_up >= MIN_MARGIN else None
        return Detection(code=decided, confidence=share, ranking=tuple(scores))
