"""FastAPI application implementing the C6 parity API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tools.parity_web import __version__
from tools.parity_web.runner import Runner
from tools.parity_web.store import RunStore

_DEFAULT_DB = Path.home() / ".oarumi" / "parity.db"
_STATIC_DIR = Path(__file__).resolve().parent / "static"


# --- pydantic models ----------------------------------------------------


class RunCreateRequest(BaseModel):
    corpus: str = Field(..., min_length=1)
    targets: list[str] = Field(..., min_length=1)


class RunCreateResponse(BaseModel):
    run_id: str
    status: str


class HealthResponse(BaseModel):
    ok: bool
    python: str
    android: str


# --- canonicalisation ---------------------------------------------------


def _canonical(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip ephemeral fields; mirrors tools.parity_runner._canonical."""
    if result is None:
        return None
    out: dict[str, Any] = json.loads(json.dumps(result))
    out.pop("request_id", None)
    for ev in out.get("failover_events", []):
        ev.pop("t", None)
    for payload in out.get("modalities", {}).values():
        payload.pop("audio_path", None)
        payload.pop("duration_ms", None)
        if payload.get("backend") in {"espeak", "android", "native"}:
            payload["backend"] = "native"
    return out


def _compute_diffs(run: dict[str, Any]) -> dict[str, Any]:
    target_results: dict[str, Any] = run.get("target_results", {})
    py = (target_results.get("python") or {}).get("payload")
    out: dict[str, Any] = {
        "run_id": run["id"],
        "corpus": run["corpus"],
        "python_vs_gold": [],
        "android_vs_gold": [],
        "python_vs_android": [],
    }

    py_cases: dict[str, dict[str, Any]] = {}
    if py is not None:
        py_cases = {c["case_id"]: c for c in py.get("cases", [])}
        for cid, case in sorted(py_cases.items()):
            if case.get("match") is False or case.get("error"):
                out["python_vs_gold"].append(
                    {
                        "case_id": cid,
                        "got": _canonical(case.get("got")),
                        "expected": _canonical(case.get("expected")),
                        "error": case.get("error"),
                    }
                )

    # Prefer "android"; fall back to "kotlin" (same backend).
    other = target_results.get("android") or target_results.get("kotlin")
    other_payload = (other or {}).get("payload")
    other_cases: dict[str, dict[str, Any]] = {}
    if other_payload is not None:
        other_cases = {c["case_id"]: c for c in other_payload.get("cases", [])}
        for cid, case in sorted(other_cases.items()):
            if case.get("match") is False or case.get("error"):
                out["android_vs_gold"].append(
                    {
                        "case_id": cid,
                        "got": _canonical(case.get("got")),
                        "expected": _canonical(case.get("expected")),
                        "error": case.get("error"),
                    }
                )

    for cid in sorted(set(py_cases) & set(other_cases)):
        p = _canonical(py_cases[cid].get("got"))
        a = _canonical(other_cases[cid].get("got"))
        if p is not None and a is not None and p != a:
            out["python_vs_android"].append(
                {
                    "case_id": cid,
                    "python": p,
                    "android": a,
                }
            )

    return out


# --- app factory --------------------------------------------------------


def create_app(
    *,
    runner: Runner | None = None,
    store: RunStore | None = None,
    run_inline: bool = False,
) -> FastAPI:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        for task in app.state.tasks:
            task.cancel()

    app = FastAPI(title="Oarumi Parity", version=__version__, lifespan=_lifespan)

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    app.state.runner = runner or Runner()
    app.state.store = store or RunStore(_DEFAULT_DB)
    app.state.tasks = []
    app.state.run_inline = run_inline

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(ok=True, python=__version__, android=__version__)

    @app.get("/api/runs")
    async def list_runs(limit: int = 50) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = app.state.store.list_runs(limit=min(max(limit, 1), 500))
        return runs

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        run: dict[str, Any] | None = app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    @app.post("/api/runs", response_model=RunCreateResponse)
    async def create_run(req: RunCreateRequest) -> RunCreateResponse:
        try:
            run_id = app.state.store.create_run(req.corpus, req.targets)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        coro = app.state.runner.run(run_id, req.corpus, req.targets, app.state.store)
        if app.state.run_inline:
            await coro
        else:
            task = asyncio.create_task(coro)
            app.state.tasks.append(task)
        run = app.state.store.get_run(run_id)
        return RunCreateResponse(run_id=run_id, status=run["status"])

    @app.get("/api/diff/{run_id}")
    async def get_diff(run_id: str) -> dict[str, Any]:
        run = app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return _compute_diffs(run)

    @app.get("/api/gold/{run_id}/{case_id}")
    async def get_gold(run_id: str, case_id: str) -> dict[str, Any]:
        run = app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        for target_name, target in run.get("target_results", {}).items():
            payload = target.get("payload")
            if payload is None:
                continue
            for case in payload.get("cases", []):
                if case.get("case_id") == case_id:
                    return {
                        "run_id": run_id,
                        "case_id": case_id,
                        "target": target_name,
                        "expected": _canonical(case.get("expected")),
                        "got": _canonical(case.get("got")),
                        "match": case.get("match"),
                        "error": case.get("error"),
                    }
        raise HTTPException(status_code=404, detail="case not found")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Serve the frontend shell. Batch 15 fills in the full SPA."""
        shell = _STATIC_DIR / "index.html"
        if shell.exists():
            return HTMLResponse(shell.read_text(encoding="utf-8"))
        return HTMLResponse(
            "<!doctype html><html><body><h1>Oarumi Parity</h1>"
            "<p>Frontend shell not yet installed (Batch 15).</p>"
            "<p>API: <a href='/api/health'>/api/health</a>, "
            "<a href='/api/runs'>/api/runs</a></p></body></html>"
        )

    return app
