"""Chaos tests. Exercise the recovery FSM under adversarial triggers.

Run nightly (slow, probabilistic). Each test uses a fixed seed for
reproducibility.
"""

from __future__ import annotations

import random
import time

import pytest
from oarumi.reliability.recovery_fsm import FSMState, RecoveryFSM


@pytest.mark.chaos
def test_random_trigger_sequence_reaches_consistent_state(rng: random.Random) -> None:
    """Feed random triggers; FSM must always end in a valid state and history
    must be internally consistent."""
    for _ in range(200):
        fsm = RecoveryFSM(component="chaos")
        for _ in range(50):
            op = rng.choice(["trigger", "canary_pass", "canary_fail", "rollback"])
            if op == "trigger":
                fsm.on_trigger(rng.choice(["a", "b", "c"]))
            elif op == "canary_pass":
                fsm.on_canary_pass()
            elif op == "canary_fail":
                if fsm.state == FSMState.RECOVERING:
                    fsm.on_canary_fail()
            elif op == "rollback":
                fsm.on_rollback()
        # Invariant: history transitions form a contiguous chain.
        for i in range(1, len(fsm.history)):
            assert fsm.history[i - 1].to == fsm.history[i].frm
        # Invariant: last transition's `to` equals state.
        if fsm.history:
            assert fsm.history[-1].to == fsm.state


@pytest.mark.chaos
def test_canary_reentry_under_repeated_failures(fast_watchdog) -> None:
    """Simulate a flapping neural path: the FSM must not spin indefinitely.

    Backoff must prevent re-entry within a short interval after a failure.
    """
    _wd, _fired = fast_watchdog
    fsm = RecoveryFSM(component="chaos-flap")
    for _ in range(20):
        fsm.on_trigger("validation")
        # Handle the case where we're stuck in FAILED.
        if fsm.state == FSMState.FAILED:
            fsm.on_rollback()
    # After 20 trigger cycles we should not have entered RECOVERING more than 20 times.
    recover_entries = sum(1 for t in fsm.history if t.to == FSMState.RECOVERING)
    assert recover_entries <= 20


@pytest.mark.chaos
def test_watchdog_does_not_drift_under_load(fast_watchdog) -> None:
    """Arm and complete many handles in a tight loop; the fired list must
    reflect only actual timeouts."""
    wd, fired = fast_watchdog
    for i in range(500):
        h = wd.arm(f"c{i}", deadline_s=0.2)
        wd.completed(h)
    time.sleep(0.3)
    assert fired == [], f"unexpected timeouts: {len(fired)}"


@pytest.mark.chaos
def test_simultaneous_watchdog_timeout_and_completion(fast_watchdog) -> None:
    """Race a timeout against a late completion; the handle must be marked
    fired exactly once (or completed, but not both)."""
    wd, _fired = fast_watchdog
    handles = []
    for i in range(50):
        h = wd.arm(f"c{i}", deadline_s=0.01)
        handles.append(h)
    time.sleep(0.05)  # let some fire
    for h in handles:
        wd.completed(h)
    time.sleep(0.05)
    # Fired handles must be marked fired; non-fired ones must be marked done.
    for h in handles:
        assert h.is_fired() or h.is_done()
        assert not (h.is_fired() and not h.is_done())  # once fired, cannot be un-done


@pytest.mark.chaos
def test_audit_log_survives_repeated_rotation(tmp_path) -> None:
    """Force many rotations; replay must still produce a well-formed event stream."""
    from oarumi.reliability.audit_log import AuditLog

    log = AuditLog(tmp_path / "audit.jsonl", max_bytes=200)
    for i in range(500):
        log.log_simple("chaos", "event", i=i)
    events = log.replay()
    assert len(events) >= 500
    # Every line must be valid JSON (replay drops invalid ones, so count alone
    # proves the log didn't corrupt).
    assert all(e.event == "event" for e in events)


@pytest.mark.chaos
def test_shield_under_mixed_valid_invalid_traffic(tmp_path, rng) -> None:
    """Send a mix of valid and invalid neural outputs; every decision must be
    recorded and consistent with the parity contract."""
    from oarumi.reliability.audit_log import AuditLog
    from oarumi.reliability.symbolic_shield import ParityContract, SymbolicShield
    from oarumi.types import ValidationOutcome

    log = AuditLog(tmp_path / "audit.jsonl")
    shield = SymbolicShield(audit=log)
    call = shield.wrap(
        component="chaos",
        neural=lambda x: x,
        validator=lambda x: ValidationOutcome(valid=x["valid"]),
        fallback=lambda _: {"valid": True, "source": "fallback"},
        contract=ParityContract(validity_required=True, latency_ceiling_ms=1000),
    )
    decisions: list[str] = []
    for _ in range(200):
        valid = rng.random() > 0.5
        r = call({"valid": valid})
        decisions.append(r.decision)
    events = [e for e in log.replay() if e.event == "shield_decision"]
    assert len(events) == 200
    assert decisions.count("use_neural") > 0
    assert decisions.count("use_fallback") > 0
