"""The Settings tab: pending edits, validation, secrets, reveal and live effects."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit

from desktop.settings.manager import EnvManager
from desktop.settings.registry import GROUPS
from desktop.settings.store import KeyringSecretStore, SettingsFile
from desktop.tests.keyring_fake import MemoryKeyring, unusable_backend
from desktop.views.settings import SettingsView

SECRET = "tab-SECRET-5150"


@pytest.fixture()
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture()
def restore_log_level() -> Iterator[None]:
    root = logging.getLogger()
    previous = root.level
    yield
    root.setLevel(previous)


def _manager(tmp_path: Path, environ: dict[str, str] | None = None) -> EnvManager:
    return EnvManager(
        KeyringSecretStore(),
        SettingsFile(tmp_path / "settings.json"),
        environ if environ is not None else {},
    )


def _view(tmp_path: Path, environ: dict[str, str] | None = None) -> SettingsView:
    return SettingsView(_manager(tmp_path, environ))


def _set_offline(view: SettingsView, on: bool) -> None:
    box = view._rows["OARUMI_OFFLINE"]._control
    assert isinstance(box, QCheckBox)
    box.setChecked(on)


def _set_log_level(view: SettingsView, level: str) -> None:
    combo = view._rows["OARUMI_LOG_LEVEL"]._control
    assert isinstance(combo, QComboBox)
    combo.setCurrentText(level)


def test_one_page_per_group_and_the_tab_is_selectable(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    labels = [view._categories.item(i).text() for i in range(view._categories.count())]
    assert labels == list(GROUPS)
    assert view._pages.count() == len(GROUPS)


def test_toggle_is_pending_until_saved(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    _set_offline(view, True)
    assert view.has_pending_changes()
    assert "1 unsaved change" in view._summary.text()
    assert not (tmp_path / "settings.json").exists()

    assert view.save() is True
    assert not view.has_pending_changes()
    assert "OARUMI_OFFLINE" in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_setting_back_to_the_saved_value_is_not_a_change(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    _set_offline(view, True)
    view.save()
    view = _view(tmp_path)
    _set_offline(view, False)
    _set_offline(view, True)
    assert not view.has_pending_changes()


def test_invalid_value_blocks_the_whole_save(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    _set_offline(view, True)
    home = view._rows["OARUMI_HOME"]._control
    assert isinstance(home, QLineEdit)
    home.setText(str(tmp_path / "does-not-exist"))

    assert view.save() is False
    assert view.has_pending_changes()
    assert not (tmp_path / "settings.json").exists()
    assert "does not exist" in view._rows["OARUMI_HOME"]._error.text()


def test_reset_removes_the_saved_value(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring, restore_log_level: None
) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_LOG_LEVEL", "DEBUG")
    view = SettingsView(mgr)
    assert view._rows["OARUMI_LOG_LEVEL"].value() == "DEBUG"

    view._rows["OARUMI_LOG_LEVEL"]._reset.click()
    assert view.save() is True
    entry = next(e for e in mgr.entries() if e.name == "OARUMI_LOG_LEVEL")
    assert not entry.is_set
    assert entry.source == "default"


def test_log_level_applies_without_a_restart(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring, restore_log_level: None
) -> None:
    view = _view(tmp_path)
    _set_log_level(view, "DEBUG")
    view.save()
    assert logging.getLogger().level == logging.DEBUG
    assert view._banner.isHidden()  # no restart needed for log level


def test_restart_banner_for_settings_that_need_a_restart(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    _set_offline(view, True)
    view.save()
    assert not view._banner.isHidden()
    assert "OARUMI_OFFLINE" in view._banner_text.text()


def test_revert_discards_pending_edits(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    _set_offline(view, True)
    view.revert()
    assert not view.has_pending_changes()
    assert view._rows["OARUMI_OFFLINE"].value() == "0"


def test_shell_override_is_shown_and_explained(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path, {"OARUMI_LOG_LEVEL": "ERROR"})
    row = view._rows["OARUMI_LOG_LEVEL"]
    assert row._badge.text() == "Shell override"
    assert "shell" in row._note.text().lower()
    assert "Active now: ERROR" in row._meta.text()


def test_secret_is_stored_in_the_keychain_and_never_shown(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._new_secret_name.setText("OARUMI_API_TOKEN")
    view._new_secret_value.setText(SECRET)
    view._on_add_secret()
    assert view.has_pending_changes()
    assert view.save() is True

    assert memory_keyring.data[("oarumi", "OARUMI_API_TOKEN")] == SECRET
    assert SECRET not in (tmp_path / "settings.json").read_text(encoding="utf-8")
    row = view._secret_rows["OARUMI_API_TOKEN"]
    assert row._input.text() == ""
    assert row._revealed.isHidden()


def test_reveal_is_visible_on_request_and_hidden_again(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._new_secret_name.setText("OARUMI_API_TOKEN")
    view._new_secret_value.setText(SECRET)
    view._on_add_secret()
    view.save()

    view._on_reveal_toggled("OARUMI_API_TOKEN")
    row = view._secret_rows["OARUMI_API_TOKEN"]
    assert row._revealed.text() == SECRET
    assert not row._revealed.isHidden()

    view._hide_reveal()
    assert row._revealed.isHidden()
    assert row._revealed.text() == ""


def test_leaving_the_tab_hides_a_revealed_secret(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._new_secret_name.setText("OARUMI_API_TOKEN")
    view._new_secret_value.setText(SECRET)
    view._on_add_secret()
    view.save()
    view.show()
    view._on_reveal_toggled("OARUMI_API_TOKEN")

    view.hide()
    assert view._revealed is None
    assert view._secret_rows["OARUMI_API_TOKEN"]._revealed.isHidden()


def test_secret_is_refused_without_a_usable_keychain(qapp: QApplication, tmp_path: Path) -> None:
    previous = keyring.get_keyring()
    keyring.set_keyring(unusable_backend("null"))
    try:
        view = _view(tmp_path)
        view._new_secret_name.setText("OARUMI_API_TOKEN")
        view._new_secret_value.setText(SECRET)
        view._on_add_secret()
        assert view.save() is False
    finally:
        keyring.set_keyring(previous)
    assert not (tmp_path / "settings.json").exists()
    assert "No usable keychain" in view._secret_rows["OARUMI_API_TOKEN"]._error.text()


def test_custom_plain_variable_can_be_added(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._custom_name.setText("OARUMI_MY_NOTE")
    view._custom_value.setText("hello")
    view._on_add_custom()
    assert view.save() is True
    assert "hello" in (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "OARUMI_MY_NOTE" in view._rows


def test_custom_page_sends_secret_looking_names_to_the_secrets_page(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._custom_name.setText("OARUMI_MY_TOKEN")
    view._custom_value.setText(SECRET)
    view._on_add_custom()
    assert not view.has_pending_changes()
    assert not view._custom_error.isHidden()
    assert "Secrets page" in view._custom_error.text()


def test_search_filters_settings_by_name_and_description(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    view = _view(tmp_path)
    view._search.setText("offline")
    assert not view._rows["OARUMI_OFFLINE"].isHidden()
    assert view._rows["OARUMI_LOG_LEVEL"].isHidden()
    view._search.setText("")
    assert not view._rows["OARUMI_LOG_LEVEL"].isHidden()


def test_corrupt_settings_file_is_reported_not_fatal(
    qapp: QApplication, tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    (tmp_path / "settings.json").write_text("{", encoding="utf-8")
    view = _view(tmp_path)
    assert not view._load_label.isHidden()
    assert "could not be read" in view._load_label.text()
    assert "OARUMI_OFFLINE" in view._rows  # registry rows still render
