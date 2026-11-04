"""End-to-end: create a run, poll it, fetch diff, fetch failover data."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tools.parity_web.api import create_app
from tools.parity_web.store import RunStore
from tools.parity_web.tests.conftest import FakeRunner


@pytest.mark.asyncio()
async def test_create_poll_diff_cycle(tmp_path: Path) -> None:
    """Simulate the SPA's request sequence for a completed run."""
    store = RunStore(tmp_path / "runs.db")
    app = create_app(
        runner=FakeRunner(fail_cases={"case_b"}),
        store=store,
        run_inline=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. SPA calls POST /api/runs.
        r = await client.post(
            "/api/runs",
            json={
                "corpus": "parity-basic",
                "targets": ["python", "kotlin"],
            },
        )
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # 2. SPA polls GET /api/runs/{id} until terminal.
        for _ in range(5):
            run_r = await client.get(f"/api/runs/{run_id}")
            run = run_r.json()
            if run["status"] in ("done", "failed", "partial"):
                break
            await asyncio.sleep(0.05)
        assert run["status"] in ("done", "failed", "partial")

        # 3. SPA calls GET /api/diff/{id} to render the diff view.
        diff = (await client.get(f"/api/diff/{run_id}")).json()
        assert len(diff["python_vs_gold"]) == 1
        assert diff["python_vs_gold"][0]["case_id"] == "case_b"

        # 4. SPA calls GET /api/gold/{run_id}/{case_id} when a row is clicked.
        gold = (await client.get(f"/api/gold/{run_id}/case_a")).json()
        assert gold["case_id"] == "case_a"
        assert gold["match"] is True

        # 5. SPA calls GET /api/runs to populate the "all runs" table.
        runs = (await client.get("/api/runs")).json()
        assert any(r["id"] == run_id for r in runs)
