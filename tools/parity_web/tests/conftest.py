"""Fixtures for parity-web tests. Uses a temp SQLite store and a fake runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tools.parity_web.api import create_app
from tools.parity_web.runner import Runner
from tools.parity_web.store import RunStore


class FakeRunner(Runner):
    """Deterministic runner used in tests.

    Each target returns a canned parity_runner-style report. Cases where
    `fail_cases` includes the case_id produce `match: false`, and cases in
    `degrade_cases` produce a degraded-but-valid result.
    """

    def __init__(
        self,
        *,
        fail_cases: set[str] | None = None,
        android_diverges_on: set[str] | None = None,
        error_on: set[str] | None = None,
    ) -> None:
        super().__init__()
        self.fail_cases = fail_cases or set()
        self.android_diverges_on = android_diverges_on or set()
        self.error_on = error_on or set()

    async def run(
        self,
        run_id: str,
        corpus: str,
        targets: list[str],
        store: RunStore,
    ) -> None:
        store.mark_running(run_id)
        errors: list[str] = []
        for target in targets:
            if target in self.error_on:
                store.complete_target(run_id, target, error=f"{target}: simulated failure")
                errors.append(target)
                continue
            payload = self._payload(target, corpus)
            store.complete_target(run_id, target, payload=payload)
        store.finish_run(run_id, error="; ".join(errors) if errors else None)

    def _payload(self, target: str, corpus: str) -> dict[str, Any]:
        cases = ["case_a", "case_b", "case_c"]
        out_cases: list[dict[str, Any]] = []
        for cid in cases:
            match = cid not in self.fail_cases
            got: dict[str, Any] = {
                "pivot": {"text": f"hello-{cid}", "lang": "en", "source": "phrasebook"},
                "nsm": {"primes": [], "combinators": [], "valid": True},
                "surface": {
                    "phonemes": ["hello"],
                    "clitics": [],
                    "mood": "DECL",
                    "modality": "spoken",
                },
                "degraded": False,
                "request_id": "ignored",
            }
            if target in {"kotlin", "android"} and cid in self.android_diverges_on:
                got["pivot"]["text"] = f"a-different-{cid}"
            out_cases.append(
                {
                    "case_id": cid,
                    "match": match,
                    "got": got,
                    "expected": (
                        got
                        if match
                        else {"pivot": {"text": "expected", "lang": "en", "source": "phrasebook"}}
                    ),
                }
            )
        return {
            "corpus": corpus,
            "target": target,
            "total": len(out_cases),
            "passed": sum(1 for c in out_cases if c["match"]),
            "failed": sum(1 for c in out_cases if not c["match"]),
            "cases": out_cases,
        }


@pytest.fixture()
def store(tmp_path: Path) -> RunStore:
    return RunStore(tmp_path / "parity.db")


@pytest.fixture()
def app(store: RunStore) -> FastAPI:
    """FastAPI app with a synchronous fake runner and an isolated store."""
    return create_app(
        runner=FakeRunner(),
        store=store,
        run_inline=True,
    )


@pytest.fixture()
def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def make_report_payload(target: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "corpus": "parity-basic",
        "target": target,
        "total": len(cases),
        "passed": sum(1 for c in cases if c.get("match")),
        "failed": sum(1 for c in cases if c.get("match") is False),
        "cases": cases,
    }
