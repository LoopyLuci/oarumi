"""Intent router: classifies a request and picks an execution lane.

The router is the *first* deterministic gate. It runs before any neural or
transductive work. Its only job is to answer three questions:

    1. Can the request possibly be served with the current capabilities?
    2. If yes, is a fully deterministic path available?
    3. Otherwise, is a neural path available?

If the answer to (1) is "no", the pipeline short-circuits to a degraded result
without spending any compute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from oarumi.db import LanguageDb
from oarumi.pivot import phrasebook
from oarumi.types import Route, TranslationRequest


class CapabilitySource(Protocol):
    """Abstraction over 'what can this device do right now'."""

    def has_language(self, lang: str) -> bool: ...
    def has_modality(self, modality: str) -> bool: ...
    def is_offline(self) -> bool: ...
    def has_neural_pivot(self, src: str, dst: str) -> bool: ...
    def has_phrasebook(self, src: str) -> bool: ...


@dataclass(slots=True)
class StaticCapabilitySource:
    """Concrete CapabilitySource used in tests and in the offline default.

    Language support is decided from the phrasebook keys plus any explicitly
    registered languages. Modality support is either all-on or configurable.
    """

    db: LanguageDb
    offline: bool = False
    extra_langs: tuple[str, ...] = ()
    neural_langs: tuple[str, ...] = ()
    modalities: tuple[str, ...] = ("spoken", "signed", "tactile", "text")

    def has_language(self, lang: str) -> bool:
        if lang in self.extra_langs:
            return True
        return lang in phrasebook.supported_languages()

    def has_modality(self, modality: str) -> bool:
        return modality in self.modalities

    def is_offline(self) -> bool:
        return self.offline

    def has_neural_pivot(self, src: str, dst: str) -> bool:
        if self.offline:
            return False
        return src in self.neural_langs and dst == "en"

    def has_phrasebook(self, src: str) -> bool:
        return src in phrasebook.supported_languages()


@dataclass(slots=True)
class IntentRouter:
    source: CapabilitySource

    def route(self, req: TranslationRequest) -> Route:
        text = req.text.strip()
        if not text:
            return Route(kind="refuse", reason="empty_input")

        if not self.source.has_language(req.lang):
            return Route(kind="refuse", reason="unsupported_language", capabilities=(req.lang,))

        if not self.source.has_modality(req.modality):
            return Route(kind="refuse", reason="unsupported_modality", capabilities=(req.modality,))

        # A phrasebook hit is a fully deterministic path.
        if self.source.has_phrasebook(req.lang) and phrasebook.lookup(req.lang, text):
            return Route(
                kind="direct_deterministic", reason="phrasebook_hit", capabilities=("phrasebook",)
            )

        # Otherwise, a neural path is viable if the adapter is installed.
        if self.source.has_neural_pivot(req.lang, "en"):
            return Route(
                kind="neural_candidate",
                reason="neural_pivot_available",
                capabilities=("pivot_adapter",),
            )

        # Nothing worked: refuse deterministically rather than crash downstream.
        return Route(kind="refuse", reason="no_pivot_path", capabilities=(req.lang,))
