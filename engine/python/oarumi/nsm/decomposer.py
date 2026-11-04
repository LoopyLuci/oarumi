"""Tier A (deterministic) NSM decomposer."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.errors import ValidationError
from oarumi.nsm.templates import TEMPLATES
from oarumi.types import NSMStructure


class NSMDecomposerTierA:
    def __init__(self, db: LanguageDb) -> None:
        self._db = db
        self._known_primes: frozenset[str] = frozenset(p.id for p in db.all_primes())

    def decompose(self, pivot: str) -> NSMStructure:
        text = pivot.strip()
        if not text:
            raise ValidationError("empty pivot", errors=["empty pivot"])

        for template in TEMPLATES:
            match = template.pattern.match(text)
            if match is None:
                continue
            nsm = template.build(match)
            self._check_known(nsm)
            return nsm

        raise ValidationError(
            f"no template matched pivot {text[:60]!r}",
            errors=[f"no-template:{text[:40]}"],
        )

    def _check_known(self, nsm: NSMStructure) -> None:
        unknown: list[str] = []
        for p in nsm.primes:
            if p.id not in self._known_primes:
                unknown.append(p.id)
        for c in nsm.combinators:
            if c.head not in self._known_primes:
                unknown.append(c.head)
            for a in c.args:
                if a not in self._known_primes:
                    unknown.append(a)
        if unknown:
            raise ValidationError(
                f"unknown prime id(s): {sorted(set(unknown))}",
                errors=[f"unknown-prime:{u}" for u in sorted(set(unknown))],
            )
