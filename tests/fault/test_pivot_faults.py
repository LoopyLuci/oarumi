"""Pivot fault injection: unavailability, corrupt model, latency, adversarial."""

from __future__ import annotations

from oarumi.reliability.symbolic_shield import ParityContract
from oarumi.types import ValidationOutcome


def test_neural_unavailable_falls_back(shield, disable_neural) -> None:
    call = shield.wrap(
        component="pivot",
        neural=disable_neural,
        validator=lambda _: ValidationOutcome(True),
        fallback=lambda _: "phrasebook hit",
        contract=ParityContract(),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.output == "phrasebook hit"
    assert r.reason.startswith("exception:")


def test_latency_breach_falls_back(shield, inject_latency) -> None:
    call = shield.wrap(
        component="pivot",
        neural=inject_latency,
        validator=lambda _: ValidationOutcome(True),
        fallback=lambda _: "fast",
        contract=ParityContract(latency_ceiling_ms=10),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason == "latency"


def test_both_fail_refuses(shield, disable_neural) -> None:
    def bad_fallback(_: int) -> str:
        raise RuntimeError("no phrasebook")

    call = shield.wrap(
        component="pivot",
        neural=disable_neural,
        validator=lambda _: ValidationOutcome(True),
        fallback=bad_fallback,
        contract=ParityContract(),
    )
    r = call(1)
    assert r.decision == "refuse"
    assert r.output is None


def test_adversarial_input_through_validator(shield, adversarial_input) -> None:
    call = shield.wrap(
        component="pivot",
        neural=adversarial_input,
        validator=lambda x: ValidationOutcome(valid=isinstance(x, str) and "\x00" not in x),
        fallback=lambda _: "clean",
        contract=ParityContract(validity_required=True),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.output == "clean"
