"""Contract C1–C3 JSON round-trips."""

from __future__ import annotations

from oarumi.types import (
    Clitic,
    Combinator,
    NSMStructure,
    OarumiSurface,
    PrimeRef,
    TranslationRequest,
)


def test_nsm_roundtrip() -> None:
    nsm = NSMStructure(
        primes=(PrimeRef(id="SOMEONE", role="agent"), PrimeRef(id="WANT", role="predicate")),
        combinators=(Combinator(type="clause", head="WANT", args=("SOMEONE", "SOMETHING")),),
        valid=True,
    )
    again = NSMStructure.from_json(nsm.to_json())
    assert again == nsm


def test_surface_roundtrip() -> None:
    s = OarumiSurface(
        phonemes=("o", "a", "ru", "mi"),
        clitics=(Clitic(form="=ha", type="mood_declarative"),),
        mood="DECL",
        modality="spoken",
    )
    assert OarumiSurface.from_json(s.to_json()) == s
    assert s.to_string() == "o a ru mi"


def test_translation_request_to_json() -> None:
    req = TranslationRequest(text="hola", lang="es")
    j = req.to_json()
    assert j["text"] == "hola"
    assert j["lang"] == "es"
    assert j["modality"] == "spoken"
