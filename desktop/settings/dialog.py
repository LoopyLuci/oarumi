"""Qt dialog for the stored environment variables.

Secrets are masked everywhere in the UI. Reveal is an explicit click, re-masks
after ten seconds, and is cleared when the dialog closes. Values are never put
on the clipboard, in a tooltip, or in a log line.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.settings.manager import Entry, EnvManager, mask
from desktop.settings.registry import REGISTRY, is_secret_name
from desktop.settings.store import SecretBackendUnavailable

REVEAL_SECONDS = 10
COLUMNS = ("Name", "Value", "Status", "Description")
NOTICE = (
    "Secrets are kept in your OS keychain. They are never written to the project, "
    "a log or the clipboard."
)


class EntryEditor(QDialog):
    """Add a new variable, or change the value of an existing one."""

    def __init__(self, manager: EnvManager, name: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add variable" if name is None else f"Change {name}")
        self._manager = manager
        self._fixed_name = name

        self._name = QComboBox(self)
        self._name.setEditable(name is None)
        self._name.addItems(sorted(REGISTRY))
        if name is not None:
            self._name.setCurrentText(name)
            self._name.setEnabled(False)

        self._value = QLineEdit(self)
        self._value.setPlaceholderText("value")
        self._secret = QCheckBox("Store as a secret (keychain, masked)", self)
        self._secret.setChecked(is_secret_name(name or ""))
        self._error = QLabel(self)
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #b00020;")

        self._name.currentTextChanged.connect(self._sync_secret_checkbox)
        self._sync_secret_checkbox(self._name.currentText())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        form = QVBoxLayout(self)
        form.addWidget(QLabel("Name (must start with OARUMI_)", self))
        form.addWidget(self._name)
        form.addWidget(QLabel("Value", self))
        form.addWidget(self._value)
        form.addWidget(self._secret)
        form.addWidget(self._error)
        form.addWidget(buttons)

    def _sync_secret_checkbox(self, name: str) -> None:
        forced = is_secret_name(name)
        self._secret.setChecked(self._secret.isChecked() or forced)
        self._secret.setEnabled(not forced)
        self._value.setEchoMode(
            QLineEdit.EchoMode.Password if self._secret.isChecked() else QLineEdit.EchoMode.Normal
        )

    def _save(self) -> None:
        name = self._name.currentText().strip()
        value = self._value.text()
        self._error.clear()
        try:
            self._manager.set(name, value, secret=self._secret.isChecked())
        except ValueError as exc:  # messages never contain the value
            self._error.setText(str(exc))
            return
        except SecretBackendUnavailable as exc:
            QMessageBox.warning(self, "Secure storage unavailable", str(exc))
            return
        self._value.clear()
        self.accept()

    def done(self, result: int) -> None:
        self._value.clear()  # do not keep a secret in a closed widget
        super().done(result)


class SettingsDialog(QDialog):
    def __init__(self, manager: EnvManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Environment variables")
        self.resize(820, 460)
        self._manager = manager
        self._revealed: str | None = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide_revealed)

        self._table = QTableWidget(0, len(COLUMNS), self)
        self._table.setHorizontalHeaderLabels(list(COLUMNS))
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._add = QPushButton("Add…", self)
        self._change = QPushButton("Change…", self)
        self._remove = QPushButton("Remove", self)
        self._reveal = QPushButton("Reveal secret", self)
        self._add.clicked.connect(self._on_add)
        self._change.clicked.connect(self._on_change)
        self._remove.clicked.connect(self._on_remove)
        self._reveal.clicked.connect(self._on_reveal)

        actions = QHBoxLayout()
        for button in (self._add, self._change, self._remove, self._reveal):
            actions.addWidget(button)
        actions.addStretch(1)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        notice = QLabel(NOTICE, self)
        notice.setWordWrap(True)
        layout.addWidget(notice)
        layout.addWidget(self._table)
        layout.addLayout(actions)
        layout.addWidget(close)

        self._table.itemSelectionChanged.connect(self._update_buttons)
        self.refresh()

    # --- rendering ----------------------------------------------------------

    def refresh(self) -> None:
        entries = self._manager.entries()
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self._set_row(row, entry)
        self._update_buttons()

    def _set_row(self, row: int, entry: Entry) -> None:
        shown = mask(entry)
        if entry.secret and entry.name == self._revealed:
            shown = self._manager.reveal(entry.name) or shown
        status = "set" if entry.is_set else "not set"
        if entry.overridden_by_shell:
            status += " (shell overrides)"
        cells = (entry.name, shown, status, entry.description)
        for column, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Secrets get no tooltip, so the description cannot be used to peek.
            if not entry.secret:
                item.setToolTip(text)
            self._table.setItem(row, column, item)

    def _selected(self) -> Entry | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return next((e for e in self._manager.entries() if e.name == item.text()), None)

    def _update_buttons(self) -> None:
        entry = self._selected()
        self._change.setEnabled(entry is not None)
        self._remove.setEnabled(entry is not None and entry.is_set)
        self._reveal.setEnabled(entry is not None and entry.secret and entry.is_set)

    # --- actions ------------------------------------------------------------

    def _on_add(self) -> None:
        if EntryEditor(self._manager, parent=self).exec():
            self.refresh()

    def _on_change(self) -> None:
        entry = self._selected()
        if entry is not None and EntryEditor(self._manager, entry.name, self).exec():
            self.refresh()

    def _on_remove(self) -> None:
        entry = self._selected()
        if entry is None or not entry.is_set:
            return
        answer = QMessageBox.question(
            self,
            "Remove variable",
            f"Remove {entry.name}? Oarumi will fall back to its default.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._manager.unset(entry.name)
            self._hide_revealed()
            self.refresh()

    def _on_reveal(self) -> None:
        entry = self._selected()
        if entry is None or not entry.secret:
            return
        self._revealed = entry.name
        self._timer.start(REVEAL_SECONDS * 1000)
        self.refresh()

    def _hide_revealed(self) -> None:
        self._revealed = None
        self._timer.stop()
        self.refresh()

    def done(self, result: int) -> None:
        self._hide_revealed()
        super().done(result)
