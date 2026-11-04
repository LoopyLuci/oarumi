"""DB interface tests against the seeded SQLite file."""

from __future__ import annotations

from oarumi.db import LanguageDb


def test_prime_lookup(db: LanguageDb) -> None:
    p = db.get_prime("WANT")
    assert p is not None
    assert p.id == "WANT"
    assert p.spoken_form


def test_all_primes_nonempty(db: LanguageDb) -> None:
    assert len(db.all_primes()) >= 60


def test_lexeme_search(db: LanguageDb) -> None:
    hits = db.search_lexemes("who")
    assert hits
    assert hits[0].gloss.lower().startswith("interrogative") or "who" in hits[0].gloss


def test_missing_prime_returns_none(db: LanguageDb) -> None:
    assert db.get_prime("NOPE") is None
