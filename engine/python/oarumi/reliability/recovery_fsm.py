"""Recovery state machine.

States: HEALTHY -> DEGRADED -> FAILED -> RECOVERING -> HEALTHY
Recovery requires a passed canary. A failed canary returns to FAILED and
schedules a retry with exponential backoff.
"""

from __future__ import annotations

import enum
import time
from collections.abc import Callable
from dataclasses import dataclass, field


class FSMState(enum.StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


@dataclass(slots=True, frozen=True)
class Transition:
    frm: FSMState
    to: FSMState
    reason: str
    t: float


@dataclass(slots=True)
class RecoveryFSM:
    component: str
    on_transition: Callable[[Transition], None] | None = None
    state: FSMState = FSMState.HEALTHY
    attempt: int = 0
    last_retry_at: float = 0.0
    history: list[Transition] = field(default_factory=list)

    def _move(self, to: FSMState, reason: str) -> None:
        if to == FSMState.HEALTHY and self.state == FSMState.RECOVERING and reason != "canary_pass":
            raise RuntimeError("cannot enter HEALTHY from RECOVERING without reason='canary_pass'")
        transition = Transition(frm=self.state, to=to, reason=reason, t=time.monotonic())
        self.state = to
        self.history.append(transition)
        if self.on_transition is not None:
            self.on_transition(transition)

    def on_trigger(self, reason: str = "trigger") -> None:
        if self.state == FSMState.HEALTHY:
            self._move(FSMState.DEGRADED, reason)
        elif self.state == FSMState.DEGRADED:
            self._move(FSMState.FAILED, reason)

    def on_canary_pass(self) -> None:
        if self.state not in (FSMState.DEGRADED, FSMState.FAILED, FSMState.RECOVERING):
            return
        self.attempt = 0
        self._move(FSMState.RECOVERING, "canary_start")
        self._move(FSMState.HEALTHY, "canary_pass")

    def on_canary_fail(self) -> None:
        if self.state != FSMState.RECOVERING:
            self.state = FSMState.FAILED
        self.attempt += 1
        self.last_retry_at = time.monotonic()
        self._move(FSMState.FAILED, "canary_fail")

    def on_rollback(self) -> None:
        self.attempt = 0
        self._move(FSMState.FAILED, "rollback")

    def backoff_s(self, base: float = 1.0, cap: float = 60.0) -> float:
        return float(min(cap, base * (2 ** max(0, self.attempt - 1))))

    def ready_for_retry(self) -> bool:
        if self.state != FSMState.FAILED:
            return False
        return time.monotonic() - self.last_retry_at >= self.backoff_s()
