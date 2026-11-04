"""Fault-injection fixtures. Each fixture disables a component and asserts the
shield routes to the deterministic fallback with the expected trigger."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def shield(tmp_path: Path):
    """Fresh SymbolicShield with its own audit log."""
    from oarumi.reliability.audit_log import AuditLog
    from oarumi.reliability.symbolic_shield import SymbolicShield

    audit = AuditLog(tmp_path / "audit.jsonl")
    return SymbolicShield(audit=audit)


@pytest.fixture()
def disable_neural() -> Callable[[int], str]:
    def fn(_: int) -> str:
        raise RuntimeError("neural disabled")

    return fn


@pytest.fixture()
def inject_latency() -> Callable[[int], str]:
    import time

    def fn(_: int) -> str:
        time.sleep(0.05)
        return "slow"

    return fn


@pytest.fixture()
def adversarial_input() -> Callable[[int], str]:
    def fn(_: int) -> str:
        return "\x00\xff malicious payload \n\r"

    return fn
