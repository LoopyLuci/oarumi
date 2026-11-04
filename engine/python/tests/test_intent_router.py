"""IntentRouter: routing, capability gating, and refusal."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.reliability.intent_router import IntentRouter, StaticCapabilitySource
from oarumi.types import TranslationRequest


def _router(db: LanguageDb, **kwargs: object) -> IntentRouter:
    defaults: dict[str, object] = {"db": db, "offline": True}
    defaults.update(kwargs)
    return IntentRouter(source=StaticCapabilitySource(**defaults))  # type: ignore[arg-type]


def test_empty_input_refuses(db: LanguageDb) -> None:
    r = _router(db).route(TranslationRequest(text="   ", lang="es"))
    assert r.kind == "refuse"
    assert r.reason == "empty_input"


def test_unsupported_language_refuses(db: LanguageDb) -> None:
    r = _router(db).route(TranslationRequest(text="hola", lang="xx"))
    assert r.kind == "refuse"
    assert r.reason == "unsupported_language"


def test_unsupported_modality_refuses(db: LanguageDb) -> None:
    router = _router(db, modalities=("text",))
    r = router.route(TranslationRequest(text="hola", lang="es", modality="spoken"))
    assert r.kind == "refuse"
    assert r.reason == "unsupported_modality"


def test_phrasebook_hit_is_direct(db: LanguageDb) -> None:
    r = _router(db).route(TranslationRequest(text="hola", lang="es"))
    assert r.kind == "direct_deterministic"
    assert r.reason == "phrasebook_hit"


def test_neural_available_no_phrasebook(db: LanguageDb) -> None:
    router = IntentRouter(
        source=StaticCapabilitySource(
            db=db,
            offline=False,
            neural_langs=("es",),
        )
    )
    r = router.route(TranslationRequest(text="not in book", lang="es"))
    assert r.kind == "neural_candidate"
    assert r.reason == "neural_pivot_available"


def test_no_path_refuses(db: LanguageDb) -> None:
    router = _router(db)  # offline, no neural
    r = router.route(TranslationRequest(text="phrase not in book", lang="es"))
    assert r.kind == "refuse"
    assert r.reason == "no_pivot_path"
