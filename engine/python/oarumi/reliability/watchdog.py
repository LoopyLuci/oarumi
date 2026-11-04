"""Deadline tracker running on a dedicated daemon thread.

Usage:

    wd = Watchdog(on_timeout=lambda h: log(h), tick=0.05)
    wd.start()
    h = wd.arm("pivot", deadline_s=0.8)
    try:
        do_the_work()
    finally:
        wd.completed(h)   # idempotent — a second call is a no-op
    wd.stop()

The watchdog never blocks the caller. `completed()` sets an event; the background
thread notices it on its next tick and removes the handle.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class WatchdogHandle:
    component: str
    deadline_at: float
    _done: threading.Event = field(default_factory=threading.Event)
    _fired: bool = False

    def is_done(self) -> bool:
        return self._done.is_set()

    def is_fired(self) -> bool:
        return self._fired


class Watchdog:
    def __init__(
        self,
        on_timeout: Callable[[WatchdogHandle], None],
        tick: float = 0.05,
    ) -> None:
        if tick <= 0:
            raise ValueError("tick must be positive")
        self._on_timeout = on_timeout
        self._tick = tick
        self._lock = threading.Lock()
        self._handles: list[WatchdogHandle] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="oarumi-watchdog")
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def arm(self, component: str, deadline_s: float) -> WatchdogHandle:
        if deadline_s <= 0:
            raise ValueError("deadline_s must be positive")
        h = WatchdogHandle(component=component, deadline_at=time.monotonic() + deadline_s)
        with self._lock:
            self._handles.append(h)
        return h

    def completed(self, handle: WatchdogHandle) -> None:
        handle._done.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            fired: list[WatchdogHandle] = []
            with self._lock:
                still_active: list[WatchdogHandle] = []
                for h in self._handles:
                    if h._done.is_set():
                        continue
                    if now >= h.deadline_at and not h._fired:
                        h._fired = True
                        fired.append(h)
                    else:
                        still_active.append(h)
                self._handles = still_active
            for h in fired:
                with contextlib.suppress(Exception):
                    self._on_timeout(h)
            self._stop.wait(self._tick)
