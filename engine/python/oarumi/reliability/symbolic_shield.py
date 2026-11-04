"""Deterministic shield around a neural callable.

Contract:

    result = shield.wrap(
        neural=my_neural_fn,
        validator=my_validator,     # maps Out -> ValidationOutcome
        fallback=my_fallback_fn,    # maps In -> O
        contract=ParityContract(...),
        component="pivot",
    )(input)

If the neural path fails any of:
  - validation
  - latency ceiling
  - integrity / hash check (caller's responsibility, signaled via exception)
  - repeated inconsistency across two runs

the shield falls back deterministically. If the fallback also fails, the
shield refuses. Every decision is one line in the audit log.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from oarumi.reliability.audit_log import AuditLog
from oarumi.reliability.watchdog import Watchdog

In = TypeVar("In")
Out = TypeVar("Out")


@dataclass(slots=True, frozen=True)
class ParityContract:
    validity_required: bool = True
    latency_ceiling_ms: int = 2000
    require_double_run_equal: bool = False


Decision = Literal["use_neural", "use_fallback", "refuse"]


@dataclass(slots=True, frozen=True)
class ShieldResult(Generic[Out]):
    decision: Decision
    output: Out | None
    reason: str
    latency_ms: float


class SymbolicShield(Generic[In, Out]):
    def __init__(
        self,
        *,
        audit: AuditLog,
        watchdog: Watchdog | None = None,
    ) -> None:
        self._audit = audit
        self._watchdog = watchdog

    def wrap(
        self,
        *,
        component: str,
        neural: Callable[[In], Out],
        validator: Callable[[Out], Any],
        fallback: Callable[[In], Out],
        contract: ParityContract,
        normalizer: Callable[[Out], str] | None = None,
    ) -> Callable[[In], ShieldResult[Out]]:
        def _call(inp: In) -> ShieldResult[Out]:
            t0 = time.monotonic()

            # --- neural attempt ---
            neural_output: Out | None = None
            neural_reason = "ok"
            try:
                if self._watchdog is not None:
                    handle = self._watchdog.arm(component, contract.latency_ceiling_ms / 1000)
                    try:
                        neural_output = neural(inp)
                    finally:
                        self._watchdog.completed(handle)
                else:
                    neural_output = neural(inp)
            except Exception as exc:
                neural_reason = f"exception:{type(exc).__name__}"

            latency_ms = (time.monotonic() - t0) * 1000

            if neural_output is not None and neural_reason == "ok":
                outcome = validator(neural_output)
                ok = bool(getattr(outcome, "valid", False))
                if contract.validity_required and not ok:
                    neural_reason = "invalid"
                elif latency_ms > contract.latency_ceiling_ms:
                    neural_reason = "latency"
                elif contract.require_double_run_equal and normalizer is not None:
                    second = neural(inp)
                    if normalizer(neural_output) != normalizer(second):
                        neural_reason = "inconsistent"

            if neural_output is not None and neural_reason == "ok":
                self._log(component, "use_neural", {"latency_ms": latency_ms})
                return ShieldResult(
                    decision="use_neural",
                    output=neural_output,
                    reason="ok",
                    latency_ms=latency_ms,
                )

            # --- fallback attempt ---
            try:
                fb = fallback(inp)
            except Exception as exc:
                self._log(
                    component,
                    "refuse",
                    {
                        "neural_reason": neural_reason,
                        "fallback_error": type(exc).__name__,
                    },
                )
                return ShieldResult(
                    decision="refuse",
                    output=None,
                    reason=f"fallback_failed:{type(exc).__name__}",
                    latency_ms=latency_ms,
                )

            self._log(
                component,
                "use_fallback",
                {
                    "neural_reason": neural_reason,
                    "latency_ms": latency_ms,
                },
            )
            return ShieldResult(
                decision="use_fallback",
                output=fb,
                reason=neural_reason,
                latency_ms=latency_ms,
            )

        return _call

    def _log(self, component: str, decision: str, payload: dict[str, Any]) -> None:
        self._audit.log_simple(
            component=component,
            event="shield_decision",
            decision=decision,
            **payload,
        )
