"""Deterministic realizer and round-trip."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.nsm.decomposer import NSMDecomposerTierA
from oarumi.nsm.realizer import NSMRealizer

TEMPLATE_CORPUS = [
    "I want water",
    "she wants to go",
    "I see the book",
    "it is good",
    "it is bad",
    "hello",
    "thank you",
    "yes",
    "no",
    "how are you",
    "where is the bathroom",
]


def test_realize_produces_surface(db: LanguageDb) -> None:
    dec = NSMDecomposerTierA(db)
    rea = NSMRealizer(db)
    nsm = dec.decompose("I want water")
    surface = rea.realize(nsm)
    assert surface.phonemes
    assert surface.mood in {"DECL", "INTERR", "IMPER", "PROM", "EXPRESS", "VOC"}


def test_round_trip_80_percent(db: LanguageDb) -> None:
    dec = NSMDecomposerTierA(db)
    rea = NSMRealizer(db)
    matches = 0
    for text in TEMPLATE_CORPUS:
        nsm1 = dec.decompose(text)
        surface = rea.realize(nsm1)
        pivot2 = rea.to_canonical_pivot(surface)
        if not pivot2:
            continue
        nsm2 = dec.decompose(pivot2)
        if nsm1 == nsm2:
            matches += 1
    assert matches / len(TEMPLATE_CORPUS) >= 0.8


def test_canonical_pivot_round_trips(db: LanguageDb) -> None:
    dec = NSMDecomposerTierA(db)
    rea = NSMRealizer(db)
    for text in ["hello", "yes", "no"]:
        nsm = dec.decompose(text)
        surface = rea.realize(nsm)
        canonical = rea.to_canonical_pivot(surface)
        assert canonical, f"no canonical for {text!r}"
        nsm2 = dec.decompose(canonical)
        assert nsm == nsm2, f"round-trip failed for {text!r}"
