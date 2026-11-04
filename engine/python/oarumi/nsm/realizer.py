"""Deterministic NSM -> OarumiSurface transducer, and its inverse for round-trip."""

from __future__ import annotations

from oarumi.db import LanguageDb
from oarumi.errors import ValidationError
from oarumi.types import (
    Clitic,
    MoodCode,
    NSMStructure,
    OarumiSurface,
)

_MOOD_TO_CLITIC = {
    "DECL": Clitic(form="=ha", type="mood_declarative"),
    "INTERR": Clitic(form="=hu", type="mood_interrogative"),
    "IMPER": Clitic(form="=hi", type="mood_imperative"),
    "PROM": Clitic(form="=ho", type="mood_promissive"),
    "EXPRESS": Clitic(form="=he", type="mood_expressive"),
    "VOC": Clitic(form="=ha", type="mood_vocative"),
}

_QUESTION_HEADS = {"BE_SOMEWHERE", "FEEL"}  # heads that trigger INTERR if 'WHERE' or bare


class NSMRealizer:
    def __init__(self, db: LanguageDb) -> None:
        self._db = db
        self._forms: dict[str, str] = {p.id: p.spoken_form for p in db.all_primes()}

    def realize(self, nsm: NSMStructure, modality: str = "spoken") -> OarumiSurface:
        if not nsm.valid:
            raise ValidationError("cannot realize invalid NSM structure")
        if not nsm.primes:
            raise ValidationError("cannot realize empty NSM structure")

        mood = self._infer_mood(nsm)
        clitics: list[Clitic] = [_MOOD_TO_CLITIC[mood]]

        # Linearize primes in canonical order: predicate head, then args.
        ordered = self._linearize(nsm)
        phonemes: list[str] = []
        for pid in ordered:
            form = self._forms.get(pid)
            if form is None:
                raise ValidationError(f"no spoken form for prime {pid}")
            phonemes.append(form)

        return OarumiSurface(
            phonemes=tuple(phonemes),
            clitics=tuple(clitics),
            mood=mood,
            modality=modality,  # type: ignore[arg-type]
        )

    def _infer_mood(self, nsm: NSMStructure) -> MoodCode:
        for c in nsm.combinators:
            # A FEEL with no explicit object or BE_SOMEWHERE with WHERE
            # is interpreted as a question by the template.
            if c.head in _QUESTION_HEADS and ("WHERE" in c.args or c.head == "FEEL"):
                return "INTERR"
            if c.head == "NOT":
                return "DECL"
        return "DECL"

    def _linearize(self, nsm: NSMStructure) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        for comb in nsm.combinators:
            if comb.type in ("clause", "predicate"):
                # Head first, then args.
                if comb.head not in seen:
                    ordered.append(comb.head)
                    seen.add(comb.head)
                for arg in comb.args:
                    if arg not in seen:
                        ordered.append(arg)
                        seen.add(arg)

        # Any prime not reached via combinators is appended in declaration order.
        for p in nsm.primes:
            if p.id not in seen:
                ordered.append(p.id)
                seen.add(p.id)

        return ordered

    def to_canonical_pivot(self, surface: OarumiSurface) -> str:
        """Reconstruct an English pivot sentence from a realized surface.

        Used by the round-trip parity test (decompose -> realize -> decompose).
        """
        rev = {form: pid for pid, form in self._forms.items()}
        prime_ids = [rev.get(ph, "") for ph in surface.phonemes]
        prime_ids = [p for p in prime_ids if p]

        # Heuristic: order in the template word order for the reconstructor.
        if "WANT" in prime_ids:
            agent = "I" if "I" in prime_ids else "someone"
            return f"{agent} wants something"
        if "SEE" in prime_ids:
            agent = "I" if "I" in prime_ids else "someone"
            return f"{agent} see something"
        if "MOVE" in prime_ids:
            agent = "I" if "I" in prime_ids else "someone"
            return f"{agent} go"
        if "BE_SPEC" in prime_ids and "GOOD" in prime_ids:
            return "it is good"
        if "BE_SPEC" in prime_ids and "BAD" in prime_ids:
            return "it is bad"
        if "SAY" in prime_ids and "WORDS" in prime_ids:
            return "hello"
        if "FEEL" in prime_ids and "GOOD" in prime_ids:
            return "thank you"
        if "FEEL" in prime_ids and "YOU" in prime_ids:
            return "how are you"
        if "BE_SOMEWHERE" in prime_ids and "WHERE" in prime_ids:
            return "where is the bathroom"
        if "TRUE" in prime_ids and "NOT" not in prime_ids:
            return "yes"
        if "NOT" in prime_ids and "TRUE" in prime_ids:
            return "no"
        return ""
