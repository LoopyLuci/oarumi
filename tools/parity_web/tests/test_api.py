"""End-to-end API tests with a synchronous fake runner."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tools.parity_web.api import create_app
from tools.parity_web.store import RunStore
from tools.parity_web.tests.conftest import FakeRunner


@pytest.fixture()
def client(tmp_path: Path) -> AsyncClient:
    store = RunStore(tmp_path / "runs.db")
    app = create_app(runner=FakeRunner(), store=store, run_inline=True)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio()
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "python" in data
    assert "android" in data


@pytest.mark.asyncio()
async def test_create_run_and_get(client: AsyncClient) -> None:
    r = await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    assert body["status"] in {"pending", "running", "done"}

    run_id = body["run_id"]
    r2 = await client.get(f"/api/runs/{run_id}")
    assert r2.status_code == 200
    run = r2.json()
    assert run["id"] == run_id
    assert "python" in run["target_results"]


@pytest.mark.asyncio()
async def test_list_runs(client: AsyncClient) -> None:
    await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    r = await client.get("/api/runs")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio()
async def test_get_missing_run_404(client: AsyncClient) -> None:
    r = await client.get("/api/runs/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio()
async def test_create_run_rejects_empty_targets(client: AsyncClient) -> None:
    r = await client.post("/api/runs", json={"corpus": "parity-basic", "targets": []})
    assert r.status_code == 422  # pydantic validation


@pytest.mark.asyncio()
async def test_diff_no_failures(client: AsyncClient) -> None:
    r = await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    run_id = r.json()["run_id"]
    d = await client.get(f"/api/diff/{run_id}")
    assert d.status_code == 200
    diff = d.json()
    assert diff["python_vs_gold"] == []
    assert diff["android_vs_gold"] == []


@pytest.mark.asyncio()
async def test_diff_with_failures(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    app = create_app(
        runner=FakeRunner(fail_cases={"case_b"}),
        store=store,
        run_inline=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
        run_id = r.json()["run_id"]
        diff = (await c.get(f"/api/diff/{run_id}")).json()
        assert len(diff["python_vs_gold"]) == 1
        assert diff["python_vs_gold"][0]["case_id"] == "case_b"


@pytest.mark.asyncio()
async def test_diff_python_vs_android(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    app = create_app(
        runner=FakeRunner(android_diverges_on={"case_c"}),
        store=store,
        run_inline=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/runs",
            json={
                "corpus": "parity-basic",
                "targets": ["python", "kotlin"],
            },
        )
        run_id = r.json()["run_id"]
        diff = (await c.get(f"/api/diff/{run_id}")).json()
        assert len(diff["python_vs_android"]) == 1
        assert diff["python_vs_android"][0]["case_id"] == "case_c"
        assert diff["python_vs_android"][0]["python"] != diff["python_vs_android"][0]["android"]


@pytest.mark.asyncio()
async def test_gold_endpoint(client: AsyncClient) -> None:
    r = await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    run_id = r.json()["run_id"]
    g = await client.get(f"/api/gold/{run_id}/case_a")
    assert g.status_code == 200
    body = g.json()
    assert body["case_id"] == "case_a"
    assert "expected" in body
    assert "got" in body


@pytest.mark.asyncio()
async def test_gold_missing_case_404(client: AsyncClient) -> None:
    r = await client.post("/api/runs", json={"corpus": "parity-basic", "targets": ["python"]})
    run_id = r.json()["run_id"]
    g = await client.get(f"/api/gold/{run_id}/does_not_exist")
    assert g.status_code == 404


@pytest.mark.asyncio()
async def test_runner_error_recorded(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    app = create_app(
        runner=FakeRunner(error_on={"kotlin"}),
        store=store,
        run_inline=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/runs", json={"corpus": "parity-basic", "targets": ["python", "kotlin"]}
        )
        run_id = r.json()["run_id"]
        run = (await c.get(f"/api/runs/{run_id}")).json()
        assert run["status"] == "failed"
        assert "kotlin" in run["target_results"]
        assert "simulated failure" in run["target_results"]["kotlin"]["error"]


@pytest.mark.asyncio()
async def test_index_renders(client: AsyncClient) -> None:
    r = await client.get("/")
    assert r.status_code == 200
    assert "Oarumi" in r.text
