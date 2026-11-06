"""Renders TranslationResult.trace and failover_events as a scrollable tree."""

from __future__ import annotations

from oarumi.types import TranslationResult
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class TraceView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Component / step", "Path / trigger", "Reason / time"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 180)
        layout.addWidget(self.tree)

    def clear(self) -> None:
        self.tree.clear()

    def show_result(self, result: TranslationResult) -> None:
        self.tree.clear()

        trace_count = len(result.trace)
        trace_root = QTreeWidgetItem(
            ["trace", "", f"{trace_count} {'entry' if trace_count == 1 else 'entries'}"]
        )
        for entry in result.trace:
            QTreeWidgetItem(
                trace_root,
                [
                    str(entry.get("step", "")),
                    str(entry.get("path", "")),
                    str(entry.get("reason", "")),
                ],
            )
        self.tree.addTopLevelItem(trace_root)

        froot = QTreeWidgetItem(["failovers", "", f"{len(result.failover_events)} events"])
        for event in result.failover_events:
            QTreeWidgetItem(
                froot,
                [
                    str(event.get("component", "")),
                    str(event.get("trigger", "")),
                    str(event.get("t", "")),
                ],
            )
        self.tree.addTopLevelItem(froot)

        self.tree.expandAll()
