"""Canary test harness used by RecoveryFSM before promoting a neural path.

A canary is a frozen input/output pair on disk, keyed by component. Loading
`tests/parity/data/canary/<component>/*.json` yields a list of cases; the
`run` method executes each against a provided callable and reports pass/fail.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class CanaryCase:
    name: str
    input: dict[str, Any]
    expected: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CanaryResult:
    passed: bool
    total: int
    failures: tuple[str, ...]


@dataclass(slots=True)
class Canary:
    root: Path

    def load(self, component: str) -> list[CanaryCase]:
        base = self.root / component
        if not base.exists():
            return []
        cases: list[CanaryCase] = []
        for path in sorted(base.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            cases.append(
                CanaryCase(
                    name=path.stem,
                    input=data["input"],
                    expected=data["expected"],
                )
            )
        return cases

    def run(
        self,
        component: str,
        call: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> CanaryResult:
        cases = self.load(component)
        if not cases:
            return CanaryResult(passed=False, total=0, failures=("no_cases",))
        failures: list[str] = []
        for case in cases:
            try:
                got = call(case.input)
            except Exception as exc:
                failures.append(f"{case.name}:raised:{type(exc).__name__}")
                continue
            if got != case.expected:
                failures.append(f"{case.name}:mismatch")
        return CanaryResult(passed=not failures, total=len(cases), failures=tuple(failures))
