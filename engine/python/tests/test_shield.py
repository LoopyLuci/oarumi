"""SymbolicShield: pass-through, fallback on invalid, fallback on latency, refuse."""

from __future__ import annotations

import time
from pathlib import Path

from oarumi.nsm.validator import ValidationOutcome
from oarumi.reliability.audit_log import AuditLog
from oarumi.reliability.symbolic_shield import (
    ParityContract,
    SymbolicShield,
)
from oarumi.reliability.watchdog import Watchdog
from oarumi.types import NSMStructure


def _good(_: int) -> NSMStructure:
    return NSMStructure(primes=(), combinators=(), valid=True)


def _bad(_: int) -> NSMStructure:
    return NSMStructure(primes=(), combinators=(), valid=False)


def _valid(o: NSMStructure) -> ValidationOutcome:
    return ValidationOutcome(valid=o.valid, errors=())


def _fallback(_: int) -> NSMStructure:
    return NSMStructure(primes=(), combinators=(), valid=True)


def test_use_neural_when_valid(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit)
    call = shield.wrap(
        component="x",
        neural=_good,
        validator=_valid,
        fallback=_fallback,
        contract=ParityContract(validity_required=True, latency_ceiling_ms=1000),
    )
    r = call(1)
    assert r.decision == "use_neural"


def test_use_fallback_when_invalid(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit)
    call = shield.wrap(
        component="x",
        neural=_bad,
        validator=_valid,
        fallback=_fallback,
        contract=ParityContract(validity_required=True, latency_ceiling_ms=1000),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason == "invalid"


def test_use_fallback_when_latency_exceeded(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit)

    def slow(_: int) -> NSMStructure:
        time.sleep(0.05)
        return NSMStructure(primes=(), combinators=(), valid=True)

    call = shield.wrap(
        component="x",
        neural=slow,
        validator=_valid,
        fallback=_fallback,
        contract=ParityContract(validity_required=True, latency_ceiling_ms=5),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason == "latency"


def test_use_fallback_when_neural_raises(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit)

    def boom(_: int) -> NSMStructure:
        raise RuntimeError("boom")

    call = shield.wrap(
        component="x",
        neural=boom,
        validator=_valid,
        fallback=_fallback,
        contract=ParityContract(),
    )
    r = call(1)
    assert r.decision == "use_fallback"
    assert r.reason.startswith("exception:")


def test_refuse_when_both_fail(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit)

    def fb_boom(_: int) -> NSMStructure:
        raise RuntimeError("fb")

    call = shield.wrap(
        component="x",
        neural=_bad,
        validator=_valid,
        fallback=fb_boom,
        contract=ParityContract(),
    )
    r = call(1)
    assert r.decision == "refuse"
    assert r.output is None


def test_watchdog_integrated(tmp_path: Path) -> None:
    fired: list[object] = []
    wd = Watchdog(on_timeout=fired.append, tick=0.01)
    wd.start()
    try:
        audit = AuditLog(tmp_path / "audit.jsonl")
        shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=audit, watchdog=wd)
        call = shield.wrap(
            component="x",
            neural=_good,
            validator=_valid,
            fallback=_fallback,
            contract=ParityContract(latency_ceiling_ms=1000),
        )
        call(1)
        assert fired == []
    finally:
        wd.stop()


def test_decision_is_audited(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    shield: SymbolicShield[int, NSMStructure] = SymbolicShield(audit=AuditLog(log_path))
    call = shield.wrap(
        component="pivot",
        neural=_bad,
        validator=_valid,
        fallback=_fallback,
        contract=ParityContract(),
    )
    call(1)
    raw = log_path.read_text()
    assert "shield_decision" in raw
    assert "use_fallback" in raw
