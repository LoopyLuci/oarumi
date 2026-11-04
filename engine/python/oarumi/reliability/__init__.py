"""Deterministic reliability layer: router, watchdog, FSM, shield, audit, canary."""

from oarumi.reliability.audit_log import AuditEvent, AuditLog
from oarumi.reliability.canary import Canary, CanaryResult
from oarumi.reliability.intent_router import (
    CapabilitySource,
    IntentRouter,
    StaticCapabilitySource,
)
from oarumi.reliability.recovery_fsm import (
    FSMState,
    RecoveryFSM,
    Transition,
)
from oarumi.reliability.symbolic_shield import (
    Decision,
    ParityContract,
    ShieldResult,
    SymbolicShield,
)
from oarumi.reliability.watchdog import Watchdog, WatchdogHandle

__all__ = [
    "AuditEvent",
    "AuditLog",
    "Canary",
    "CanaryResult",
    "CapabilitySource",
    "Decision",
    "FSMState",
    "IntentRouter",
    "ParityContract",
    "RecoveryFSM",
    "ShieldResult",
    "StaticCapabilitySource",
    "SymbolicShield",
    "Transition",
    "Watchdog",
    "WatchdogHandle",
]
