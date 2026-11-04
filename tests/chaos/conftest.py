"""Chaos fixtures: fast watchdogs, aggressive retry, deterministic seeds."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def fast_watchdog():
    from oarumi.reliability.watchdog import Watchdog

    fired: list = []
    wd = Watchdog(on_timeout=fired.append, tick=0.005)
    wd.start()
    try:
        yield wd, fired
    finally:
        wd.stop()


@pytest.fixture()
def rng() -> random.Random:
    return random.Random(20260101)
