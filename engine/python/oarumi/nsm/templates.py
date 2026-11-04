"""Rule templates: pivot-language patterns -> NSMStructure."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from oarumi.types import Combinator, NSMStructure, PrimeRef


@dataclass(slots=True, frozen=True)
class Template:
    name: str
    pattern: re.Pattern[str]
    build: Callable[[re.Match[str]], NSMStructure]


def _ref(pid: str, role: str) -> PrimeRef:
    return PrimeRef(id=pid, role=role)  # type: ignore[arg-type]


def _clause(head: str, *args: str) -> Combinator:
    return Combinator(type="clause", head=head, args=tuple(args))


# --- individual builders ------------------------------------------------


def _build_want(m: re.Match[str]) -> NSMStructure:
    who = m.group("who").strip()
    # Map pronouns to primes.
    agent = "I" if who.lower() in {"i", "yo", "je", "ich"} else "SOMEONE"
    obj = "SOMETHING"
    primes = (_ref(agent, "agent"), _ref("WANT", "predicate"), _ref(obj, "patient"))
    combs = (_clause("WANT", agent, obj),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_see(m: re.Match[str]) -> NSMStructure:
    who = m.group("who").strip()
    m.group("what").strip()
    agent = "I" if who.lower() in {"i", "yo", "je", "ich"} else "SOMEONE"
    obj = "SOMETHING"
    primes = (_ref(agent, "agent"), _ref("SEE", "predicate"), _ref(obj, "patient"))
    combs = (_clause("SEE", agent, obj),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_go(m: re.Match[str]) -> NSMStructure:
    who = m.group("who").strip() if m.groupdict().get("who") else "SOMEONE"
    agent = "I" if who.lower() in {"i", "yo", "je", "ich"} else "SOMEONE"
    primes = (_ref(agent, "agent"), _ref("MOVE", "predicate"), _ref("WHERE", "modifier"))
    combs = (_clause("MOVE", agent, "WHERE"),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_is_good(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("SOMETHING", "patient"), _ref("BE_SPEC", "predicate"), _ref("GOOD", "argument"))
    combs = (Combinator(type="predicate", head="BE_SPEC", args=("SOMETHING", "GOOD")),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_is_bad(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("SOMETHING", "patient"), _ref("BE_SPEC", "predicate"), _ref("BAD", "argument"))
    combs = (Combinator(type="predicate", head="BE_SPEC", args=("SOMETHING", "BAD")),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_greeting(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("I", "agent"), _ref("SAY", "predicate"), _ref("WORDS", "patient"))
    combs = (_clause("SAY", "I", "WORDS"),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_thanks(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("I", "agent"), _ref("FEEL", "predicate"), _ref("GOOD", "argument"))
    combs = (Combinator(type="predicate", head="FEEL", args=("I", "GOOD")),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_yes(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("TRUE", "predicate"),)
    combs = (Combinator(type="predicate", head="TRUE", args=()),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_no(m: re.Match[str]) -> NSMStructure:
    primes = (_ref("NOT", "operator"), _ref("TRUE", "predicate"))
    combs = (Combinator(type="predicate", head="NOT", args=("TRUE",)),)
    return NSMStructure(primes=primes, combinators=combs)


def _build_question_how(m: re.Match[str]) -> NSMStructure:
    (
        _ref("YOU", "agent"),
        _ref("FEEL", "predicate"),
        _ref("HOW", "modifier") if False else _ref("FEEL", "predicate"),
    )
    # 'how are you' -> FEEL(YOU, ?); represented as FEEL with no argument.
    combs = (Combinator(type="predicate", head="FEEL", args=("YOU",)),)
    return NSMStructure(primes=(_ref("YOU", "agent"), _ref("FEEL", "predicate")), combinators=combs)


def _build_question_where(m: re.Match[str]) -> NSMStructure:
    primes = (
        _ref("SOMETHING", "patient"),
        _ref("BE_SOMEWHERE", "predicate"),
        _ref("WHERE", "modifier"),
    )
    combs = (Combinator(type="predicate", head="BE_SOMEWHERE", args=("SOMETHING", "WHERE")),)
    return NSMStructure(primes=primes, combinators=combs)


# --- registry -----------------------------------------------------------

TEMPLATES: tuple[Template, ...] = (
    Template(
        name="want",
        pattern=re.compile(
            r"^(?P<who>i|he|she|they|you|someone)\s+(?:want|wants|would like)\s+(?:to\s+)?(?P<what>.+?)"
            r"(?:\s+(?:go|eat|sleep|leave|come))?$",
            re.IGNORECASE,
        ),
        build=_build_want,
    ),
    Template(
        name="want_simple",
        pattern=re.compile(
            r"^(?P<who>i|he|she|they|you)\s+(?:want|wants)\s+(?P<what>[^.?!]+)$",
            re.IGNORECASE,
        ),
        build=_build_want,
    ),
    Template(
        name="see",
        pattern=re.compile(
            r"^(?P<who>i|he|she|they|you)\s+(?:see|sees)\s+(?:the\s+)?(?P<what>[^.?!]+)$",
            re.IGNORECASE,
        ),
        build=_build_see,
    ),
    Template(
        name="go",
        pattern=re.compile(r"^(?P<who>i|he|she|they|you)\s+(?:want to\s+)?go$", re.IGNORECASE),
        build=_build_go,
    ),
    Template(
        name="is_good",
        pattern=re.compile(r"^(?:it\s+is|it's|this\s+is)\s+good$", re.IGNORECASE),
        build=_build_is_good,
    ),
    Template(
        name="is_bad",
        pattern=re.compile(r"^(?:it\s+is|it's|this\s+is)\s+bad$", re.IGNORECASE),
        build=_build_is_bad,
    ),
    Template(
        name="hello",
        pattern=re.compile(r"^(?:hello|hi|good morning|good night)$", re.IGNORECASE),
        build=_build_greeting,
    ),
    Template(
        name="thanks",
        pattern=re.compile(r"^(?:thank you|thanks)$", re.IGNORECASE),
        build=_build_thanks,
    ),
    Template(name="yes", pattern=re.compile(r"^yes$", re.IGNORECASE), build=_build_yes),
    Template(name="no", pattern=re.compile(r"^no$", re.IGNORECASE), build=_build_no),
    Template(
        name="how_are_you",
        pattern=re.compile(r"^how\s+are\s+you$", re.IGNORECASE),
        build=_build_question_how,
    ),
    Template(
        name="where_is",
        pattern=re.compile(r"^where\s+is\s+(?:the\s+)?[^.?!]+$", re.IGNORECASE),
        build=_build_question_where,
    ),
)
