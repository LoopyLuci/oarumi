"""Settings tab: every OARUMI_* setting in one place.

Edits stay pending until Save changes. Save checks every pending value first and
writes nothing if any value is invalid, so a half-saved configuration cannot
happen. Saved secrets are never shown again; Reveal shows one for a few seconds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QHideEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.settings.manager import Entry, EnvManager
from desktop.settings.registry import (
    CUSTOM_GROUP,
    GROUPS,
    NAME_RE,
    REGISTRY,
    SECRETS_GROUP,
    Variable,
    is_secret_name,
    validate_value,
    variable_for,
)
from desktop.settings.store import SecretBackendUnavailable, SettingsError

REVEAL_SECONDS = 10
SOURCE_TEXT = {"shell": "from your shell", "saved": "saved", "default": "default"}
APPLY_TEXT = {
    "now": "Applies immediately.",
    "restart": "Applies after Oarumi restarts.",
    "next run": "Applies the next time that tool starts.",
}


@dataclass(frozen=True)
class _Pending:
    """An edit not yet saved. ``value`` None means remove the saved value."""

    value: str | None
    secret: bool


@dataclass(frozen=True)
class _Badge:
    state: str  # unsaved, shell, saved, default or locked; drives the colour
    text: str


@dataclass(frozen=True)
class _RowView:
    value: str
    editable: bool
    meta: str
    note: str
    badge: _Badge
    can_reset: bool


@dataclass(frozen=True)
class _SecretView:
    pending_text: str
    editable: bool
    status: str
    note: str
    badge: _Badge
    can_remove: bool
    remove_label: str
    revealable: bool


def _set_badge(label: QLabel, badge: _Badge) -> None:
    label.setText(badge.text)
    label.setProperty("state", badge.state)
    label.style().unpolish(label)
    label.style().polish(label)


def _page() -> tuple[QScrollArea, QVBoxLayout]:
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(4, 4, 12, 4)
    layout.setSpacing(10)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(inner)
    return scroll, layout


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("settingsHeading")
    return label


def _note(text: str, object_name: str = "settingNote") -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(True)
    return label


class SettingRow(QFrame):
    """One non-secret setting: a typed control, its explanation and its status."""

    changed = Signal(str)
    reset_requested = Signal(str)

    def __init__(self, var: Variable, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingRow")
        self._var = var

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        head = QHBoxLayout()
        title = QLabel(var.label)
        title.setObjectName("settingTitle")
        name = QLabel(var.name)
        name.setObjectName("settingName")
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._badge = QLabel()
        self._badge.setObjectName("settingBadge")
        head.addWidget(title)
        head.addWidget(name)
        head.addStretch(1)
        head.addWidget(self._badge)
        layout.addLayout(head)

        layout.addWidget(_note(var.description, "settingDesc"))

        controls = QHBoxLayout()
        self._control = self._build_control()
        controls.addWidget(self._control, 1)
        self._browse: QPushButton | None = None
        if var.kind == "path":
            self._browse = QPushButton("Browse…")
            self._browse.setObjectName("secondaryButton")
            self._browse.clicked.connect(self._choose_folder)
            controls.addWidget(self._browse)
        reset_label = "Reset to default" if var.name in REGISTRY else "Remove"
        self._reset = QPushButton(reset_label)
        self._reset.setObjectName("secondaryButton")
        self._reset.clicked.connect(lambda: self.reset_requested.emit(var.name))
        controls.addWidget(self._reset)
        layout.addLayout(controls)

        self._meta = _note("", "settingMeta")
        self._note = _note("", "settingNote")
        self._error = _note("", "settingError")
        layout.addWidget(self._meta)
        layout.addWidget(self._note)
        layout.addWidget(self._error)
        self._error.hide()

    # --- control ----------------------------------------------------------

    def _build_control(self) -> QWidget:
        var = self._var
        if var.kind == "bool":
            box = QCheckBox("On")
            box.toggled.connect(lambda *_: self._emit_changed())
            return box
        if var.kind == "choice":
            combo = QComboBox()
            combo.addItems(list(var.choices))
            combo.currentIndexChanged.connect(lambda *_: self._emit_changed())
            return combo
        if var.kind == "int":
            spin = QSpinBox()
            spin.setRange(var.minimum or 0, var.maximum or 999_999)
            spin.valueChanged.connect(lambda *_: self._emit_changed())
            return spin
        line = QLineEdit()
        if var.kind == "path":
            line.setPlaceholderText("Folder path. Leave empty to use the default.")
        else:
            line.setPlaceholderText(var.default or "Enter a value")
        line.textChanged.connect(lambda *_: self._emit_changed())
        return line

    def _emit_changed(self) -> None:
        self.changed.emit(self._var.name)

    def _choose_folder(self) -> None:
        if not isinstance(self._control, QLineEdit):
            return
        start = self._control.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose folder", start)
        if folder:
            self._control.setText(folder)

    def value(self) -> str:
        control = self._control
        if isinstance(control, QCheckBox):
            return "1" if control.isChecked() else "0"
        if isinstance(control, QComboBox):
            return control.currentText()
        if isinstance(control, QSpinBox):
            return str(control.value())
        if isinstance(control, QLineEdit):
            return control.text()
        return ""

    def _write(self, text: str) -> None:
        control = self._control
        if isinstance(control, QCheckBox):
            control.setChecked(text == "1")
        elif isinstance(control, QComboBox):
            control.setCurrentIndex(max(control.findText(text), 0))
        elif isinstance(control, QSpinBox):
            control.setValue(int(text) if text.isdigit() else control.minimum())
        elif isinstance(control, QLineEdit):
            control.setText(text)

    # --- state ------------------------------------------------------------

    def set_view(self, view: _RowView) -> None:
        """Full redraw, including the control's value. Use only when it is safe to
        replace what the user typed, such as after a save."""
        self._control.blockSignals(True)
        try:
            self._write(view.value)
        finally:
            self._control.blockSignals(False)
        self.set_status(view)

    def set_status(self, view: _RowView) -> None:
        """Update labels and buttons without touching the control's value."""
        self._control.setEnabled(view.editable)
        if self._browse is not None:
            self._browse.setEnabled(view.editable)
        self._reset.setEnabled(view.editable and view.can_reset)
        self._reset.setVisible(view.can_reset or self._var.name in REGISTRY)
        self._meta.setText(view.meta)
        self._note.setText(view.note)
        self._note.setVisible(bool(view.note))
        _set_badge(self._badge, view.badge)

    def set_error(self, text: str) -> None:
        self._error.setText(text)
        self._error.setVisible(bool(text))


class SecretRow(QFrame):
    """One secret. The stored value is never shown; Reveal is explicit and timed."""

    changed = Signal(str, str)  # name, text typed into the new-value box
    remove_requested = Signal(str)
    reveal_requested = Signal(str)

    def __init__(self, name: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingRow")
        self._name = name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        head = QHBoxLayout()
        title = QLabel(name)
        title.setObjectName("settingTitle")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._badge = QLabel()
        self._badge.setObjectName("settingBadge")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._badge)
        layout.addLayout(head)

        layout.addWidget(_note(description, "settingDesc"))

        entry_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setPlaceholderText("Type a new value to store (kept hidden)")
        self._input.textChanged.connect(lambda text: self.changed.emit(self._name, text))
        entry_row.addWidget(self._input, 1)
        self._reveal = QPushButton("Reveal")
        self._reveal.setObjectName("secondaryButton")
        self._reveal.clicked.connect(lambda: self.reveal_requested.emit(self._name))
        entry_row.addWidget(self._reveal)
        self._remove = QPushButton("Remove")
        self._remove.setObjectName("secondaryButton")
        self._remove.clicked.connect(lambda: self.remove_requested.emit(self._name))
        entry_row.addWidget(self._remove)
        layout.addLayout(entry_row)

        self._status = _note("", "settingMeta")
        self._revealed = QLabel()
        self._revealed.setObjectName("settingRevealed")
        self._revealed.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._revealed.setWordWrap(True)
        self._revealed.hide()
        self._note = _note("", "settingNote")
        self._error = _note("", "settingError")
        layout.addWidget(self._status)
        layout.addWidget(self._revealed)
        layout.addWidget(self._note)
        layout.addWidget(self._error)
        self._error.hide()

    def set_view(self, view: _SecretView) -> None:
        self._input.blockSignals(True)
        try:
            self._input.setText(view.pending_text)
        finally:
            self._input.blockSignals(False)
        self.set_status(view)

    def set_status(self, view: _SecretView) -> None:
        self._input.setEnabled(view.editable)
        self._reveal.setEnabled(view.revealable)
        self._remove.setEnabled(view.can_remove)
        self._remove.setText(view.remove_label)
        self._status.setText(view.status)
        self._note.setText(view.note)
        self._note.setVisible(bool(view.note))
        _set_badge(self._badge, view.badge)

    def set_revealed(self, value: str | None) -> None:
        """Show a stored value for a moment, or hide it again when ``value`` is None."""
        self._revealed.setText(value or "")
        self._revealed.setVisible(value is not None)
        self._reveal.setText("Hide" if value is not None else "Reveal")

    def set_error(self, text: str) -> None:
        self._error.setText(text)
        self._error.setVisible(bool(text))


class SettingsView(QWidget):
    """The Settings tab. Emits ``restart_requested`` when the user asks to restart."""

    status_message = Signal(str)
    restart_requested = Signal()

    def __init__(self, manager: EnvManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._pending: dict[str, _Pending] = {}
        self._errors: dict[str, str] = {}
        self._entries: dict[str, Entry] = {}
        self._load_error = ""
        self._rows: dict[str, SettingRow] = {}
        self._secret_rows: dict[str, SecretRow] = {}
        self._searchable: list[tuple[QWidget, str]] = []
        self._revealed: tuple[str, str] | None = None
        self._keychain_name: str | None = None

        self._reveal_timer = QTimer(self)
        self._reveal_timer.setSingleShot(True)
        self._reveal_timer.timeout.connect(self._hide_reveal)

        self._build_chrome()
        self._refresh()

    # --- construction -----------------------------------------------------

    def _build_chrome(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search settings by name or description")
        self._search.textChanged.connect(self._apply_filter)
        outer.addWidget(self._search)

        self._load_label = _note("", "settingError")
        self._load_label.hide()
        outer.addWidget(self._load_label)

        self._banner = QFrame()
        self._banner.setObjectName("restartBanner")
        banner = QHBoxLayout(self._banner)
        self._banner_text = QLabel()
        self._banner_text.setWordWrap(True)
        banner.addWidget(self._banner_text, 1)
        restart = QPushButton("Restart Oarumi now")
        restart.clicked.connect(lambda: self.restart_requested.emit())
        later = QPushButton("Later")
        later.setObjectName("secondaryButton")
        later.clicked.connect(self._banner.hide)
        banner.addWidget(restart)
        banner.addWidget(later)
        self._banner.hide()
        outer.addWidget(self._banner)

        body = QHBoxLayout()
        self._categories = QListWidget()
        self._categories.setObjectName("settingsCategories")
        self._categories.setFixedWidth(210)
        for group in GROUPS:
            item = QListWidgetItem(group)
            item.setData(Qt.ItemDataRole.UserRole, group)
            self._categories.addItem(item)
        self._pages = QStackedWidget()
        self._categories.currentRowChanged.connect(self._pages.setCurrentIndex)
        body.addWidget(self._categories)
        body.addWidget(self._pages, 1)
        outer.addLayout(body, 1)

        footer = QHBoxLayout()
        self._path_label = _note(f"Saved to {self._manager.settings_path}", "settingMeta")
        self._path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        open_folder = QPushButton("Open settings folder")
        open_folder.setObjectName("secondaryButton")
        open_folder.clicked.connect(self.open_settings_folder)
        footer.addWidget(self._path_label, 1)
        footer.addWidget(open_folder)
        footer.addStretch(1)
        self._summary = QLabel()
        self._summary.setObjectName("settingMeta")
        self._revert = QPushButton("Revert")
        self._revert.setObjectName("secondaryButton")
        self._revert.clicked.connect(self.revert)
        self._save = QPushButton("Save changes")
        self._save.clicked.connect(self.save)
        footer.addWidget(self._summary)
        footer.addWidget(self._revert)
        footer.addWidget(self._save)
        outer.addLayout(footer)

    # --- rendering --------------------------------------------------------

    def _load_entries(self) -> dict[str, Entry]:
        try:
            entries = {e.name: e for e in self._manager.entries()}
        except SettingsError as exc:
            self._load_error = str(exc)
            self._load_label.setText(
                f"The settings file could not be read ({exc}). Fix or delete it, "
                "then reopen this tab. Saving will also fail until it is readable."
            )
            self._load_label.show()
            return {}
        self._load_error = ""
        self._load_label.hide()
        return entries

    def _refresh(self) -> None:
        """Rebuild every page from the file and the pending edits."""
        current = max(self._categories.currentRow(), 0)
        self._hide_reveal()
        self._entries = self._load_entries()
        self._keychain_name = self._manager.secret_backend_name()
        self._rows.clear()
        self._secret_rows.clear()
        self._searchable.clear()
        while self._pages.count():
            old = self._pages.widget(0)
            if old is None:
                break
            self._pages.removeWidget(old)
            old.deleteLater()

        names = sorted(set(REGISTRY) | set(self._entries) | set(self._pending))
        by_group: dict[str, list[str]] = {group: [] for group in GROUPS}
        secrets: list[str] = []
        for name in names:
            if self._is_secret(name):
                secrets.append(name)
            else:
                by_group.setdefault(variable_for(name).group, []).append(name)

        for group in GROUPS:
            if group == SECRETS_GROUP:
                page = self._secrets_page(secrets)
            elif group == CUSTOM_GROUP:
                page = self._custom_page(by_group[group])
            else:
                page = self._plain_page(group, by_group[group])
            self._pages.addWidget(page)

        self._categories.setCurrentRow(current)
        self._pages.setCurrentIndex(current)
        self._mark_sidebar()
        self._update_footer()
        self._apply_filter(self._search.text())

    def _plain_page(self, group: str, names: list[str]) -> QScrollArea:
        page, layout = _page()
        layout.addWidget(_heading(group))
        if not names:
            layout.addWidget(_note("Nothing to configure here."))
        for name in names:
            var = variable_for(name)
            row = SettingRow(var)
            row.changed.connect(self._on_row_changed)
            row.reset_requested.connect(self._on_reset)
            row.set_view(self._row_view(name))
            row.set_error(self._errors.get(name, ""))
            self._rows[name] = row
            self._searchable.append((row, f"{name} {var.label} {var.description}".lower()))
            layout.addWidget(row)
        layout.addStretch(1)
        return page

    def _custom_page(self, names: list[str]) -> QScrollArea:
        page, layout = _page()
        layout.addWidget(_heading(CUSTOM_GROUP))
        layout.addWidget(
            _note(
                "Add any OARUMI_* variable that Oarumi does not list yet. Values are "
                "plain text. For anything sensitive, use the Secrets page."
            )
        )
        layout.addWidget(self._custom_form())
        if not names:
            layout.addWidget(_note("No custom variables yet."))
        for name in names:
            var = variable_for(name)
            row = SettingRow(var)
            row.changed.connect(self._on_row_changed)
            row.reset_requested.connect(self._on_reset)
            row.set_view(self._row_view(name))
            row.set_error(self._errors.get(name, ""))
            self._rows[name] = row
            self._searchable.append((row, f"{name} {var.description}".lower()))
            layout.addWidget(row)
        layout.addStretch(1)
        return page

    def _secrets_page(self, names: list[str]) -> QScrollArea:
        page, layout = _page()
        layout.addWidget(_heading(SECRETS_GROUP))
        layout.addWidget(
            _note(
                "Secrets are stored in your OS keychain. Oarumi never writes them to "
                "settings.json, a log or the clipboard. Saved secrets stay hidden; "
                f"Reveal shows one for {REVEAL_SECONDS} seconds."
            )
        )
        if self._keychain_name is None:
            layout.addWidget(
                _note(
                    "No usable keychain was found. Secrets cannot be saved on this machine, "
                    "and Oarumi will not fall back to a plain file.",
                    "settingError",
                )
            )
        else:
            layout.addWidget(_note(f"Keychain in use: {self._keychain_name}.", "settingMeta"))
        layout.addWidget(self._secret_form())
        if not names:
            layout.addWidget(_note("No secrets stored yet."))
        for name in names:
            var = variable_for(name)
            row = SecretRow(name, var.description)
            row.changed.connect(self._on_secret_changed)
            row.remove_requested.connect(self._on_secret_remove)
            row.reveal_requested.connect(self._on_reveal_toggled)
            row.set_view(self._secret_view(name))
            row.set_error(self._errors.get(name, ""))
            self._secret_rows[name] = row
            self._searchable.append((row, f"{name} secret".lower()))
            layout.addWidget(row)
        layout.addStretch(1)
        return page

    def _custom_form(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("addForm")
        layout = QVBoxLayout(frame)
        layout.addWidget(_heading("Add a custom variable"))
        line = QHBoxLayout()
        self._custom_name = QLineEdit()
        self._custom_name.setPlaceholderText("OARUMI_MY_SETTING")
        self._custom_value = QLineEdit()
        self._custom_value.setPlaceholderText("value")
        add = QPushButton("Add")
        add.clicked.connect(self._on_add_custom)
        line.addWidget(self._custom_name, 1)
        line.addWidget(self._custom_value, 1)
        line.addWidget(add)
        layout.addLayout(line)
        self._custom_error = _note("", "settingError")
        self._custom_error.hide()
        layout.addWidget(self._custom_error)
        return frame

    def _secret_form(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("addForm")
        layout = QVBoxLayout(frame)
        layout.addWidget(_heading("Add a secret"))
        line = QHBoxLayout()
        self._new_secret_name = QLineEdit()
        self._new_secret_name.setPlaceholderText("OARUMI_MY_TOKEN")
        self._new_secret_value = QLineEdit()
        self._new_secret_value.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_secret_value.setPlaceholderText("value (kept hidden)")
        add = QPushButton("Add")
        add.clicked.connect(self._on_add_secret)
        line.addWidget(self._new_secret_name, 1)
        line.addWidget(self._new_secret_value, 1)
        line.addWidget(add)
        layout.addLayout(line)
        self._secret_error = _note("", "settingError")
        self._secret_error.hide()
        layout.addWidget(self._secret_error)
        return frame

    # --- view models ------------------------------------------------------

    def _is_secret(self, name: str) -> bool:
        pend = self._pending.get(name)
        if pend is not None and pend.value is not None:
            return pend.secret or variable_for(name).secret
        entry = self._entries.get(name)
        if entry is not None:
            return entry.secret
        return variable_for(name).secret

    def _group_of(self, name: str) -> str:
        return SECRETS_GROUP if self._is_secret(name) else variable_for(name).group

    def _row_view(self, name: str) -> _RowView:
        var = variable_for(name)
        entry = self._entries.get(name)
        pend = self._pending.get(name)
        stored = entry.value if entry is not None else None
        if pend is None:
            value = stored if stored is not None else var.default
        elif pend.value is None:
            value = var.default
        else:
            value = pend.value
        source = entry.source if entry is not None else "default"
        active = entry.effective if entry is not None and entry.effective else var.default

        if var.shell_only:
            badge = _Badge("locked", "Read only")
            note = "Read from your shell only. Set it there, then restart Oarumi."
        elif pend is not None:
            badge = _Badge("unsaved", "Unsaved change")
            note = ""
        elif source == "shell":
            badge = _Badge("shell", "Shell override")
            note = "Your shell sets this. Oarumi uses the shell value until you unset it there."
        elif source == "saved":
            badge = _Badge("saved", "Saved")
            note = ""
        else:
            badge = _Badge("default", "Default")
            note = ""

        meta = (
            f"Active now: {active or '(not set)'} ({SOURCE_TEXT[source]}).  "
            f"Default: {var.default or '(none)'}."
        )
        if not var.shell_only:
            meta += f"  {APPLY_TEXT[var.apply]}"
        can_reset = not var.shell_only and (pend is not None or stored is not None)
        return _RowView(
            value=value,
            editable=not var.shell_only,
            meta=meta,
            note=note,
            badge=badge,
            can_reset=can_reset,
        )

    def _secret_view(self, name: str) -> _SecretView:
        entry = self._entries.get(name)
        pend = self._pending.get(name)
        stored = entry is not None and entry.is_set
        pending_text = ""
        if pend is None:
            status = "Stored in your keychain." if stored else "Not set."
            badge = _Badge("saved", "Saved") if stored else _Badge("default", "Not set")
            remove_label = "Remove"
        elif pend.value is None:
            status = "Will be removed when you save."
            badge = _Badge("unsaved", "Unsaved change")
            remove_label = "Keep"
        else:
            status = "New value ready. Save changes to store it."
            badge = _Badge("unsaved", "Unsaved change")
            pending_text = pend.value
            remove_label = "Remove"
        editable = self._keychain_name is not None
        note = "" if editable else "No usable keychain. Secrets cannot be changed here."
        return _SecretView(
            pending_text=pending_text,
            editable=editable,
            status=status,
            note=note,
            badge=badge,
            can_remove=stored or pend is not None,
            remove_label=remove_label,
            revealable=stored and editable,
        )

    # --- edits ------------------------------------------------------------

    def _on_row_changed(self, name: str) -> None:
        var = variable_for(name)
        self._errors.pop(name, None)
        new = self._rows[name].value()
        entry = self._entries.get(name)
        stored = entry.value if entry is not None else None
        base = stored if stored is not None else var.default
        if var.kind == "path" and not new:
            # An empty folder means "use the default", which is the same as removing it.
            if stored is not None:
                self._pending[name] = _Pending(None, False)
            else:
                self._pending.pop(name, None)
        elif new == base:
            self._pending.pop(name, None)
        else:
            self._pending[name] = _Pending(new, False)
        self._rows[name].set_status(self._row_view(name))
        self._after_edit()

    def _on_reset(self, name: str) -> None:
        entry = self._entries.get(name)
        if entry is not None and entry.is_set:
            self._pending[name] = _Pending(None, False)
        else:
            self._pending.pop(name, None)
        self._errors.pop(name, None)
        self._refresh()

    def _on_secret_changed(self, name: str, text: str) -> None:
        self._errors.pop(name, None)
        pend = self._pending.get(name)
        if text:
            self._pending[name] = _Pending(text, True)
        elif pend is not None and pend.value is not None:
            self._pending.pop(name)
        self._secret_rows[name].set_status(self._secret_view(name))
        self._after_edit()

    def _on_secret_remove(self, name: str) -> None:
        entry = self._entries.get(name)
        stored = entry is not None and entry.is_set
        pend = self._pending.get(name)
        self._errors.pop(name, None)
        if pend is not None and pend.value is None:
            self._pending.pop(name)  # undo a pending removal
        elif stored:
            self._pending[name] = _Pending(None, True)
        elif pend is not None:
            self._pending.pop(name)  # a new value that was never stored
        self._refresh()

    def _on_add_custom(self) -> None:
        name = self._custom_name.text().strip()
        value = self._custom_value.text()
        error = ""
        if not NAME_RE.match(name):
            error = "Names must look like OARUMI_SOMETHING (capitals, digits and underscores)."
        elif name in REGISTRY:
            error = f"{name} already has its own page."
        elif is_secret_name(name):
            error = (
                "Names with TOKEN, KEY, PASSWORD, SECRET or CREDENTIAL are stored as "
                "secrets. Add them on the Secrets page."
            )
        elif not value:
            error = "Enter a value."
        if error:
            self._custom_error.setText(error)
            self._custom_error.show()
            return
        self._pending[name] = _Pending(value, False)
        self._custom_name.clear()
        self._custom_value.clear()
        self._custom_error.hide()
        self._refresh()
        self.status_message.emit(f"{name} added. Save changes to store it.")

    def _on_add_secret(self) -> None:
        name = self._new_secret_name.text().strip()
        value = self._new_secret_value.text()
        error = ""
        if not NAME_RE.match(name):
            error = "Names must look like OARUMI_SOMETHING (capitals, digits and underscores)."
        elif name in REGISTRY and not REGISTRY[name].secret:
            error = f"{name} is a setting, not a secret. Set it on its own page."
        elif not value:
            error = "Enter a value."
        if error:
            self._secret_error.setText(error)
            self._secret_error.show()
            return
        self._pending[name] = _Pending(value, True)
        self._new_secret_name.clear()
        self._new_secret_value.clear()
        self._secret_error.hide()
        self._refresh()
        self.status_message.emit(f"{name} added. Save changes to store it.")

    def _after_edit(self) -> None:
        self._mark_sidebar()
        self._update_footer()

    def has_pending_changes(self) -> bool:
        return bool(self._pending)

    def revert(self) -> None:
        if not self._pending:
            return
        self._pending.clear()
        self._errors.clear()
        self._refresh()
        self.status_message.emit("Unsaved settings changes discarded.")

    def save(self) -> bool:
        """Validate and write every pending change. Returns False if nothing was written."""
        if not self._pending:
            return True
        errors = self._validate_pending()
        if errors:
            self._errors = errors
            self._refresh()
            self.status_message.emit(f"Nothing saved. Fix {len(errors)} setting(s) first.")
            return False

        values = dict(self._pending)
        saved: list[str] = []
        current = ""
        try:
            for current, pend in values.items():
                if pend.value is None:
                    self._manager.unset(current)
                else:
                    self._manager.set(current, pend.value, secret=pend.secret)
                saved.append(current)
        except (SecretBackendUnavailable, SettingsError, ValueError) as exc:
            # Keep the edits that were not written so the user can fix and retry.
            self._pending = {n: p for n, p in self._pending.items() if n not in saved}
            self._errors = {current: str(exc)}
            self._refresh()
            self.status_message.emit(f"Could not save {current}. {exc}")
            return False

        self._pending.clear()
        self._errors.clear()
        self._apply_live(values)
        self._refresh()
        self.status_message.emit(f"Saved {len(saved)} setting(s).")
        needs_restart = [n for n in saved if variable_for(n).apply == "restart"]
        if needs_restart:
            self._banner_text.setText("Restart Oarumi to apply: " + ", ".join(needs_restart) + ".")
            self._banner.show()
        return True

    def _validate_pending(self) -> dict[str, str]:
        errors: dict[str, str] = {}
        keychain_ok = self._manager.secret_backend_name() is not None
        for name, pend in self._pending.items():
            var = variable_for(name)
            if not NAME_RE.match(name):
                errors[name] = "Names must look like OARUMI_SOMETHING."
                continue
            if var.shell_only:
                errors[name] = "Read from the shell only. It cannot be saved here."
                continue
            if pend.value is None:
                continue
            if pend.secret and not keychain_ok:
                errors[name] = "No usable keychain. This secret cannot be saved."
                continue
            try:
                validate_value(var, pend.value)
            except ValueError as exc:
                errors[name] = str(exc)
        return errors

    def _apply_live(self, values: dict[str, _Pending]) -> None:
        """Apply the settings that do not need a restart."""
        level = values.get("OARUMI_LOG_LEVEL")
        if level is not None:
            text = level.value or REGISTRY["OARUMI_LOG_LEVEL"].default
            logging.getLogger().setLevel(text)

    def _update_footer(self) -> None:
        count = len(self._pending)
        if count:
            plural = "" if count == 1 else "s"
            self._summary.setText(f"{count} unsaved change{plural}")
        else:
            self._summary.setText("No unsaved changes")
        self._save.setEnabled(count > 0)
        self._revert.setEnabled(count > 0)

    def _mark_sidebar(self) -> None:
        dirty = {self._group_of(name) for name in self._pending}
        for index in range(self._categories.count()):
            item = self._categories.item(index)
            group = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"{group}  •" if group in dirty else group)

    def _apply_filter(self, text: str) -> None:
        query = text.strip().lower()
        for widget, haystack in self._searchable:
            widget.setVisible(not query or query in haystack)

    # --- reveal -----------------------------------------------------------

    def _on_reveal_toggled(self, name: str) -> None:
        if self._revealed is not None and self._revealed[0] == name:
            self._hide_reveal()
            return
        self._hide_reveal()
        entry = self._entries.get(name)
        if entry is None or not entry.is_set:
            self.status_message.emit(f"No stored value for {name}.")
            return
        try:
            value = self._manager.reveal(name)
        except SecretBackendUnavailable as exc:
            self.status_message.emit(str(exc))
            return
        if value is None:
            self.status_message.emit(f"No stored value for {name}.")
            return
        self._revealed = (name, value)
        self._secret_rows[name].set_revealed(value)
        self._reveal_timer.start(REVEAL_SECONDS * 1000)
        self.status_message.emit(f"{name} is visible for {REVEAL_SECONDS} seconds.")

    def _hide_reveal(self) -> None:
        if self._revealed is None:
            return
        name, _ = self._revealed
        self._revealed = None
        self._reveal_timer.stop()
        row = self._secret_rows.get(name)
        if row is not None:
            row.set_revealed(None)

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802 (Qt override name)
        # Leaving the tab must not leave a secret on screen.
        self._hide_reveal()
        super().hideEvent(event)

    # --- misc -------------------------------------------------------------

    def open_settings_folder(self) -> None:
        folder = self._manager.settings_path.parent
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
