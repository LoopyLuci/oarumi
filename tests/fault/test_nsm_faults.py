"""NSM fault injection: invalid structure must route to refusal or fallback."""

from __future__ import annotations

from oarumi.nsm.validator import ValidationOutcome as NsmOutcome  # re-exported alias
from oarumi.reliability.symbolic_shield import ParityContract
from oarumi.types import Combinator, NSMStructure, PrimeRef


def test_invalid_nsm_falls_back(shield) -> None:
    def bad_neural(_: int) -> NSMStructure:
        return NSMStructure(
            primes=(PrimeRef("NOT_A_PRIME", "agent"),),
            combinators=(Combinator("clause", "WANT", ()),),
            valid=True,
        )

    def validator(nsm: NSMStructure) -> NsmOutcome:
        known = {"I", "SOMEONE", "WANT", "SOMETHING"}
        ok = all(p.id in known for p in nsm.primes)
        return NsmOutcome(valid=ok, errors=() if ok else ("unknown_prime",))

    call = shield.wrap(
        component="nsm_decompose",
        neural=bad_neural,
        validator=validator,
        fallback=lambda _: NSMStructure(primes=(), combinators=(), valid=False),
        contract=ParityContract(validity_required=True),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason == "invalid"


def test_valid_nsm_used(shield) -> None:
    def good_neural(_: int) -> NSMStructure:
        return NSMStructure(
            primes=(PrimeRef("I", "agent"), PrimeRef("WANT", "predicate")),
            combinators=(Combinator("clause", "WANT", ("I", "SOMETHING")),),
            valid=True,
        )

    call = shield.wrap(
        component="nsm_decompose",
        neural=good_neural,
        validator=lambda nsm: NsmOutcome(valid=nsm.valid),
        fallback=lambda _: NSMStructure(primes=(), combinators=(), valid=False),
        contract=ParityContract(validity_required=True),
    )
    r = call(1)
    assert r.decision == "use_neural"
