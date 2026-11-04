"""Server entry point reads host and port from the environment."""

from __future__ import annotations

from typing import Any

import pytest
import uvicorn

from tools.parity_web import server


def test_main_binds_to_env_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run(app: object, **kwargs: Any) -> None:
        calls["app"] = app
        calls.update(kwargs)

    sentinel = object()
    monkeypatch.setattr(server, "create_app", lambda: sentinel)
    monkeypatch.setattr(uvicorn, "run", fake_run)
    monkeypatch.setenv("OARUMI_PARITY_HOST", "127.0.0.1")
    monkeypatch.setenv("OARUMI_PARITY_PORT", "8123")

    assert server.main([]) == 0
    assert calls["app"] is sentinel
    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 8123


def test_main_defaults_to_port_8090(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    monkeypatch.setattr(server, "create_app", lambda: object())
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: calls.update(kw))
    monkeypatch.delenv("OARUMI_PARITY_HOST", raising=False)
    monkeypatch.delenv("OARUMI_PARITY_PORT", raising=False)

    server.main()
    assert calls["port"] == 8090
    assert calls["host"] == "127.0.0.1"
