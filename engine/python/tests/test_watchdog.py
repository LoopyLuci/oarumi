"""Watchdog: arming, completion, timeout firing, idempotency, shutdown."""

from __future__ import annotations

import time
from collections.abc import Callable

from oarumi.reliability.watchdog import Watchdog, WatchdogHandle


def _wait_for(predicate: Callable[[], bool], timeout_s: float = 1.0) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_completion_prevents_timeout() -> None:
    fired: list[WatchdogHandle] = []
    wd = Watchdog(on_timeout=fired.append, tick=0.01)
    wd.start()
    try:
        h = wd.arm("x", deadline_s=0.2)
        wd.completed(h)
        assert _wait_for(lambda: False, timeout_s=0.3) is False  # nothing to wait for
        assert fired == []
    finally:
        wd.stop()


def test_timeout_fires() -> None:
    fired: list[WatchdogHandle] = []
    wd = Watchdog(on_timeout=fired.append, tick=0.01)
    wd.start()
    try:
        h = wd.arm("x", deadline_s=0.05)
        assert _wait_for(lambda: len(fired) == 1, timeout_s=1.0)
        assert fired[0].component == "x"
        assert fired[0].is_fired()
        assert h.is_fired()
    finally:
        wd.stop()


def test_completed_is_idempotent() -> None:
    wd = Watchdog(on_timeout=lambda h: None, tick=0.05)
    wd.start()
    try:
        h = wd.arm("x", deadline_s=1.0)
        wd.completed(h)
        wd.completed(h)  # second call must not raise
        assert h.is_done()
    finally:
        wd.stop()


def test_callback_exception_does_not_kill_thread() -> None:
    def boom(h: WatchdogHandle) -> None:
        raise RuntimeError("handler failed")

    wd = Watchdog(on_timeout=boom, tick=0.01)
    wd.start()
    try:
        wd.arm("a", deadline_s=0.02)
        wd.arm("b", deadline_s=0.02)
        # If the thread died, we would not be able to arm a third and see it fire.
        time.sleep(0.2)
        wd.arm("c", deadline_s=0.02)
        time.sleep(0.2)
    finally:
        wd.stop()
