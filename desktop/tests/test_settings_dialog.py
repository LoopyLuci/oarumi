"""Settings dialog: secrets are masked in the UI and only revealed on request."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from desktop.settings.dialog import EntryEditor, SettingsDialog
from desktop.settings.manager import MASK, EnvManager
from desktop.settings.store import KeyringSecretStore, SettingsFile
from desktop.tests.keyring_fake import MemoryKeyring

SECRET = "dialog-SECRET-7731"


@pytest.fixture()
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


def _mgr(tmp_path: Path) -> EnvManager:
    return EnvManager(KeyringSecretStore(), SettingsFile(tmp_path / "settings.json"), {})


def _all_cell_text(dialog: SettingsDialog) -> str:
    table = dialog._table
    texts: list[str] = []
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None:
                texts.append(item.text())
    return "\n".join(texts)


def _select(dialog: SettingsDialog, name: str) -> int:
    for row in range(dialog._table.rowCount()):
        item = dialog._table.item(row, 0)
        if item is not None and item.text() == name:
            dialog._table.selectRow(row)
            return row
    raise AssertionError(f"{name} not in table")


def test_secret_is_masked_everywhere_in_the_table(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _mgr(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    dialog = SettingsDialog(mgr)
    text = _all_cell_text(dialog)
    assert SECRET not in text
    assert MASK in text
    row = _select(dialog, "OARUMI_API_TOKEN")
    item = dialog._table.item(row, 0)
    assert item is not None
    assert SECRET not in item.toolTip()
    dialog.done(0)


def test_reveal_shows_the_value_then_masks_again(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _mgr(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    dialog = SettingsDialog(mgr)
    _select(dialog, "OARUMI_API_TOKEN")

    dialog._on_reveal()
    assert SECRET in _all_cell_text(dialog)

    dialog._hide_revealed()
    assert SECRET not in _all_cell_text(dialog)
    dialog.done(0)


def test_plain_value_is_shown_and_reveal_is_disabled(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _mgr(tmp_path)
    mgr.set("OARUMI_LOG_LEVEL", "DEBUG")
    dialog = SettingsDialog(mgr)
    _select(dialog, "OARUMI_LOG_LEVEL")
    assert "DEBUG" in _all_cell_text(dialog)
    assert not dialog._reveal.isEnabled()
    dialog.done(0)


def test_editor_saves_a_secret_with_masked_input(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _mgr(tmp_path)
    editor = EntryEditor(mgr)
    editor._name.setCurrentText("OARUMI_API_TOKEN")
    assert editor._secret.isChecked()
    assert not editor._secret.isEnabled()  # forced by the name
    assert editor._value.echoMode() == QLineEdit.EchoMode.Password

    editor._value.setText(SECRET)
    editor._save()
    assert mgr.reveal("OARUMI_API_TOKEN") == SECRET
    assert editor._value.text() == ""  # cleared after saving
    editor.done(0)


def test_editor_shows_validation_error_without_the_value(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    editor = EntryEditor(_mgr(tmp_path))
    editor._name.setCurrentText("OARUMI_LOG_LEVEL")
    editor._value.setText("TRACE")
    editor._save()
    assert "must be one of" in editor._error.text()
    assert "TRACE" not in editor._error.text()
    editor.done(0)
