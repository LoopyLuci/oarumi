"""Model-level fault injection: corrupt weights and memory starvation must fall back."""

from __future__ import annotations

import pytest
from oarumi.nsm.validator import ValidationOutcome as NsmOutcome
from oarumi.reliability.symbolic_shield import ParityContract
from oarumi.types import NSMStructure


def _fallback(_: int) -> NSMStructure:
    return NSMStructure(primes=(), combinators=(), valid=False)


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (ValueError("corrupt weights"), "exception:ValueError"),
        (MemoryError("arena exhausted"), "exception:MemoryError"),
    ],
    ids=["corrupt_model", "starve_memory"],
)
def test_neural_exception_routes_to_fallback(shield, error: Exception, reason: str) -> None:
    def neural(_: int) -> NSMStructure:
        raise error

    call = shield.wrap(
        component="nsm_decompose",
        neural=neural,
        validator=lambda nsm: NsmOutcome(valid=nsm.valid),
        fallback=_fallback,
        contract=ParityContract(validity_required=True),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason == reason
