"""Offline fixtures: monkeypatch every network primitive to fail loudly."""

from __future__ import annotations

import socket
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_socket(*_: object, **__: object) -> None:
        raise AssertionError("network call attempted during offline test")

    monkeypatch.setattr(socket, "socket", _fail_socket)
    monkeypatch.setattr(socket, "create_connection", _fail_socket)

    def _fail_urlopen(*_: object, **__: object) -> None:
        raise AssertionError("urllib.request.urlopen called during offline test")

    monkeypatch.setattr(urllib.request, "urlopen", _fail_urlopen)
    monkeypatch.setenv("OARUMI_OFFLINE", "1")
