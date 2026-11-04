"""Symbolic shield for NSM structures."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.types import NSMStructure, ValidationOutcome

__all__ = ["NSMValidator", "ValidationOutcome"]


class NSMValidator:
    def __init__(self, db: LanguageDb) -> None:
        self._known = frozenset(p.id for p in db.all_primes())

    def validate(self, nsm: NSMStructure) -> ValidationOutcome:
        errors: list[str] = []

        if not nsm.primes:
            errors.append("no primes")
        if not nsm.combinators:
            errors.append("no combinators")

        seen_primes: set[str] = set()
        for p in nsm.primes:
            if p.id not in self._known:
                errors.append(f"unknown prime: {p.id}")
            if p.id in seen_primes:
                errors.append(f"duplicate prime: {p.id}")
            seen_primes.add(p.id)

        for c in nsm.combinators:
            if c.type not in ("clause", "predicate", "modifier", "quote", "conditional"):
                errors.append(f"bad combinator type: {c.type}")
            if c.head not in self._known:
                errors.append(f"unknown head: {c.head}")
            for a in c.args:
                if a not in self._known:
                    errors.append(f"unknown arg: {a}")

        return ValidationOutcome(valid=not errors, errors=tuple(errors))
