"""RecoveryFSM: transitions, canary gating, backoff, history."""

from __future__ import annotations

import pytest
from oarumi.reliability.recovery_fsm import FSMState, RecoveryFSM


def test_healthy_to_degraded_to_failed() -> None:
    fsm = RecoveryFSM(component="pivot")
    fsm.on_trigger("validation")
    assert _state(fsm) == FSMState.DEGRADED
    fsm.on_trigger("validation")
    assert _state(fsm) == FSMState.FAILED


def _state(fsm: RecoveryFSM) -> FSMState:
    # Reads through a helper so the type checker does not narrow across trigger calls.
    return fsm.state


def test_cannot_go_healthy_without_canary_pass() -> None:
    fsm = RecoveryFSM(component="pivot")
    fsm.on_trigger("x")
    with pytest.raises(RuntimeError):
        # Private but load-bearing invariant; safe to assert via the public API.
        fsm._move(FSMState.RECOVERING, "manual")
        fsm._move(FSMState.HEALTHY, "manual")


def test_canary_pass_recovers() -> None:
    fsm = RecoveryFSM(component="pivot")
    fsm.on_trigger("x")
    fsm.on_canary_pass()
    assert fsm.state == FSMState.HEALTHY
    assert fsm.attempt == 0


def test_canary_fail_schedules_retry() -> None:
    fsm = RecoveryFSM(component="pivot")
    fsm.on_trigger("x")
    fsm.on_canary_pass.__name__  # noqa: B018 - keep import meaning
    fsm.state = FSMState.RECOVERING
    fsm.on_canary_fail()
    assert fsm.state == FSMState.FAILED
    assert fsm.attempt == 1
    assert fsm.ready_for_retry() is False


def test_backoff_grows() -> None:
    fsm = RecoveryFSM(component="pivot")
    assert fsm.backoff_s() == 1.0
    fsm.attempt = 1
    assert fsm.backoff_s() == 1.0
    fsm.attempt = 2
    assert fsm.backoff_s() == 2.0
    fsm.attempt = 10
    assert fsm.backoff_s() == 60.0  # cap


def test_history_records_every_transition() -> None:
    fsm = RecoveryFSM(component="pivot")
    fsm.on_trigger("a")
    fsm.on_trigger("b")
    fsm.on_canary_pass()
    reasons = [t.reason for t in fsm.history]
    assert "a" in reasons
    assert "b" in reasons
    assert "canary_pass" in reasons
    assert fsm.history[0].frm == FSMState.HEALTHY
    assert fsm.history[-1].to == FSMState.HEALTHY
