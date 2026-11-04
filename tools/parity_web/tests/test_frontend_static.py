"""DOM smoke test for the parity web frontend.

Verifies that the SPA shell is served, that all referenced assets resolve,
and that the required public JS surfaces are present. No browser required.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tools.parity_web.api import create_app
from tools.parity_web.store import RunStore

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@pytest.fixture()
def client(tmp_path: Path) -> AsyncClient:
    store = RunStore(tmp_path / "runs.db")
    app = create_app(runner=None, store=store, run_inline=True)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio()
async def test_index_served(client: AsyncClient) -> None:
    r = await client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Oarumi Parity" in body
    assert 'id="app"' in body
    assert 'id="health"' in body
    assert 'data-route="overview"' in body
    assert 'data-route="runs"' in body


@pytest.mark.asyncio()
async def test_all_static_assets_reachable(client: AsyncClient) -> None:
    for name in ("style.css", "app.js", "diff.js", "failover.js"):
        r = await client.get(f"/static/{name}")
        assert r.status_code == 200, f"{name} returned {r.status_code}"
        assert r.text.strip(), f"{name} is empty"


@pytest.mark.asyncio()
async def test_index_references_all_scripts(client: AsyncClient) -> None:
    r = await client.get("/")
    body = r.text
    for src in ("/static/diff.js", "/static/failover.js", "/static/app.js", "/static/style.css"):
        assert src in body, f"{src} not referenced in index.html"


def test_app_js_exposes_public_surface() -> None:
    source = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    # API client
    for name in ("health", "listRuns", "getRun", "createRun", "getDiff", "getGold"):
        assert name in source, f"api.{name} not exposed in app.js"
    # Views
    for name in ("overview", "runDetail", "runsList", "diff", "failover"):
        assert name in source, f"views.{name} not defined in app.js"
    # Namespace
    assert "window.Oarumi" in source
    assert "NS.api" in source
    assert "NS.views" in source


def test_diff_js_exposes_public_surface() -> None:
    source = (STATIC_DIR / "diff.js").read_text(encoding="utf-8")
    assert "window.Oarumi" in source
    for name in ("render", "flatten", "compare"):
        assert (
            f"{name}," in source or f"{name}:" in source or f"function {name}" in source
        ), f"diff.{name} not defined"


def test_failover_js_exposes_public_surface() -> None:
    source = (STATIC_DIR / "failover.js").read_text(encoding="utf-8")
    assert "window.Oarumi" in source
    for name in ("render", "summarise"):
        assert f"function {name}" in source, f"failover.{name} not defined"


def test_index_has_no_external_cdn_references() -> None:
    """No build step, no CDN — the SPA must work fully offline."""
    body = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "cdn." not in body
    assert "unpkg." not in body
    assert "jsdelivr." not in body
    assert (
        "https://" not in body or body.count("https://") == 0
    ), "index.html must not reference external URLs"


def test_no_external_dependencies_in_js() -> None:
    for name in ("app.js", "diff.js", "failover.js"):
        source = (STATIC_DIR / name).read_text(encoding="utf-8")
        assert "import " not in source, f"{name} must not use ES modules (no build step)"
        assert "require(" not in source, f"{name} must not use CommonJS"
        # Sanity: no CDN fetches.
        assert 'fetch("https://' not in source
        assert "fetch('https://" not in source
