"""Persistent status bar: offline indicator, degraded badge, audit tail."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from desktop.state import AppState


class StatusBarWidget(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)

        self._offline = QLabel()
        self._offline.setObjectName("badge_offline")
        layout.addWidget(self._offline)

        self._degraded = QLabel()
        self._degraded.setObjectName("badge_degraded")
        layout.addWidget(self._degraded)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(sep)

        self._audit_tail = QLabel()
        self._audit_tail.setObjectName("audit_tail")
        self._audit_tail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._audit_tail, 1)

        self._refresh_btn = QToolButton()
        self._refresh_btn.setText("↻")
        self._refresh_btn.setToolTip("Refresh audit tail")
        self._refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_btn)

        self.refresh()

    def refresh(self) -> None:
        cfg = self._state.cfg
        if cfg.offline:
            self._offline.setText("Offline")
            self._offline.setProperty("severity", "info")
        else:
            self._offline.setText("Online")
            self._offline.setProperty("severity", "ok")
        self._restyle(self._offline)

        result = self._state.last_result
        if result is None:
            self._degraded.setText("")
            self._degraded.setVisible(False)
        else:
            degraded = result.degraded
            self._degraded.setVisible(degraded)
            if degraded:
                self._degraded.setText("Degraded")
                self._degraded.setProperty("severity", "warn")
                self._restyle(self._degraded)

        self._audit_tail.setText(self._tail_text())

    def _tail_text(self) -> str:
        path: Path = self._state.audit.path
        if not path.exists():
            return "(no audit events yet)"
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()[-3:]
        except OSError as exc:
            return f"(audit unreadable: {exc})"
        parts: list[str] = []
        for raw in lines:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            parts.append(f"{data.get('component')}:{data.get('event')}")
        return "  ·  ".join(parts) if parts else "(no audit events yet)"

    @staticmethod
    def _restyle(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
