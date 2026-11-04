"""Symbolic shield for NSM."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.nsm.validator import NSMValidator
from oarumi.types import Combinator, NSMStructure, PrimeRef


def test_valid_nsm_passes(db: LanguageDb) -> None:
    nsm = NSMStructure(
        primes=(PrimeRef("I", "agent"), PrimeRef("WANT", "predicate")),
        combinators=(Combinator("clause", "WANT", ("I", "SOMETHING")),),
    )
    assert NSMValidator(db).validate(nsm).valid


def test_unknown_prime_fails(db: LanguageDb) -> None:
    nsm = NSMStructure(
        primes=(PrimeRef("NOT_A_PRIME", "agent"),),
        combinators=(Combinator("clause", "WANT", ()),),
    )
    outcome = NSMValidator(db).validate(nsm)
    assert not outcome.valid
    assert any("NOT_A_PRIME" in e for e in outcome.errors)


def test_empty_fails(db: LanguageDb) -> None:
    outcome = NSMValidator(db).validate(NSMStructure(primes=(), combinators=()))
    assert not outcome.valid
