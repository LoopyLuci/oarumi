"""Packs tab: install and remove language packs, and check for a new release."""

from __future__ import annotations

import urllib.error
import webbrowser
from collections.abc import Callable

from oarumi import updates
from oarumi.lang import PackEntry
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import __version__
from desktop.packs import PackManager

_COLUMNS = ("Language", "Code", "Includes", "Status", "Size")


class _Task(QThread):
    """Runs one blocking call off the UI thread and reports its result or error."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, work: Callable[[], object]) -> None:
        super().__init__()
        self._work = work

    def run(self) -> None:
        try:
            result = self._work()
        except (OSError, ValueError, urllib.error.URLError) as exc:
            self.failed.emit(str(exc))
            return
        self.done.emit(result)


class PacksView(QWidget):
    packs_changed = Signal()
    status_message = Signal(str)

    def __init__(self, manager: PackManager) -> None:
        super().__init__()
        self._manager = manager
        self._entries: list[PackEntry] = list(manager.entries())
        self._task: _Task | None = None
        self._release: updates.Release | None = None
        self._build_ui()
        self._refresh_table()

    # --- construction ---------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 12)
        outer.setSpacing(14)

        title = QLabel("Language packs")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Spelling and detection data. Base packs are built in. Extra packs download once "
            "and then work offline."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        outer.addWidget(self._build_pack_card(), 1)
        outer.addWidget(self._build_update_card())

        self._status = QLabel("")
        self._status.setObjectName("statusLine")
        outer.addWidget(self._status)

    def _build_pack_card(self) -> QFrame:
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(_COLUMNS))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(_COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._install_btn = QPushButton("Install selected")
        self._install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn = QPushButton("Remove selected")
        self._remove_btn.setObjectName("secondaryButton")
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self._remove_btn)
        buttons.addWidget(self._install_btn)
        layout.addLayout(buttons)

        self._install_btn.clicked.connect(self._on_install)
        self._remove_btn.clicked.connect(self._on_remove)
        return card

    def _build_update_card(self) -> QFrame:
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        heading = QLabel("App updates")
        heading.setObjectName("fieldLabel")
        layout.addWidget(heading)

        row = QHBoxLayout()
        self._version_label = QLabel(f"You have version {__version__}.")
        self._version_label.setObjectName("metaValue")
        row.addWidget(self._version_label)
        row.addStretch(1)
        self._check_btn = QPushButton("Check for updates")
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn = QPushButton("Open release page")
        self._open_btn.setObjectName("secondaryButton")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setVisible(False)
        row.addWidget(self._open_btn)
        row.addWidget(self._check_btn)
        layout.addLayout(row)

        self._update_result = QLabel(
            "Desktop updates are installed from the release page or with pip. "
            "The app does not replace itself."
        )
        self._update_result.setObjectName("countLabel")
        self._update_result.setWordWrap(True)
        layout.addWidget(self._update_result)

        self._check_btn.clicked.connect(self._on_check_updates)
        self._open_btn.clicked.connect(self._on_open_release)
        return card

    # --- table ----------------------------------------------------------

    def _refresh_table(self) -> None:
        selected = self._selected_code()
        self._table.setRowCount(0)
        for entry in self._entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            installed = self._manager.is_installed(entry)
            includes = "Spelling and detection" if entry.spell else "Detection"
            values = (
                entry.name,
                entry.code,
                includes,
                _status(entry, installed),
                _size(entry.size_bytes),
            )
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, entry.code)
                if column in (1, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                    )
                self._table.setItem(row, column, item)
            if entry.code == selected:
                self._table.selectRow(row)
        self._sync_buttons()

    def _selected_code(self) -> str | None:
        rows = self._table.selectionModel().selectedRows() if self._table.selectionModel() else []
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def _selected_entry(self) -> PackEntry | None:
        code = self._selected_code()
        return next((entry for entry in self._entries if entry.code == code), None)

    def _sync_buttons(self) -> None:
        entry = self._selected_entry()
        busy = self._task is not None and self._task.isRunning()
        installed = entry is not None and self._manager.is_installed(entry)
        self._install_btn.setEnabled(entry is not None and not installed and not busy)
        self._remove_btn.setEnabled(installed and not busy)
        self._check_btn.setEnabled(not busy)

    # --- actions --------------------------------------------------------

    def _on_install(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        self._run(
            f"Downloading {entry.name}…",
            lambda: self._manager.download(entry),
            f"{entry.name} installed.",
        )

    def _on_remove(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        self._manager.remove(entry)
        self._refresh_table()
        self.packs_changed.emit()
        self._show(f"{entry.name} removed.")

    def _on_check_updates(self) -> None:
        self._run_update_check()

    def _on_open_release(self) -> None:
        if self._release is not None:
            webbrowser.open(self._release.html_url)

    def _run(self, busy_text: str, work: Callable[[], object], done_text: str) -> None:
        self._show(busy_text)
        self._task = _Task(work)
        self._task.done.connect(lambda _: self._finish_pack_task(done_text))
        self._task.failed.connect(lambda message: self._fail(f"Could not finish: {message}"))
        self._sync_buttons()
        self._task.start()

    def _finish_pack_task(self, done_text: str) -> None:
        self._refresh_table()
        self.packs_changed.emit()
        self._show(done_text)

    def _run_update_check(self) -> None:
        self._update_result.setText("Checking GitHub for a new release…")
        self._task = _Task(updates.fetch_latest)
        self._task.done.connect(self._show_release)
        self._task.failed.connect(
            lambda message: self._update_result.setText(f"Could not check for updates: {message}")
        )
        self._sync_buttons()
        self._task.start()

    def _show_release(self, release: object) -> None:
        assert isinstance(release, updates.Release)
        self._release = release
        self._sync_buttons()
        if updates.is_newer(release.tag, updates.to_semver(__version__)):
            self._update_result.setText(f"Version {release.tag} is available.")
            self._open_btn.setVisible(True)
        else:
            self._update_result.setText("You are on the latest release.")
            self._open_btn.setVisible(False)

    def _fail(self, message: str) -> None:
        self._sync_buttons()
        self._show(message)

    def _show(self, text: str) -> None:
        self._status.setText(text)
        self.status_message.emit(text)


def _card() -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    return card


def _status(entry: PackEntry, installed: bool) -> str:
    if entry.base and installed:
        return "Built in"
    return "Installed" if installed else "Not installed"


def _size(size_bytes: int) -> str:
    return f"{size_bytes / 1024:,.0f} KB"
