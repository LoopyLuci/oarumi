"""EnvManager: storage rules, masking, reveal and startup loading."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from desktop.settings.manager import MASK, EnvManager, mask
from desktop.settings.store import (
    KeyringSecretStore,
    SecretBackendUnavailable,
    SettingsError,
    SettingsFile,
    StoredData,
)
from desktop.tests.keyring_fake import MemoryKeyring, unusable_backend

SECRET = "tok-PLAINTEXT-42"


@pytest.fixture()
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


def _manager(tmp_path: Path, environ: dict[str, str] | None = None) -> EnvManager:
    return EnvManager(
        KeyringSecretStore(),
        SettingsFile(tmp_path / "settings.json"),
        environ if environ is not None else {},
    )


def test_plain_value_is_stored_in_the_file(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_LOG_LEVEL", "DEBUG")
    assert "DEBUG" in (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert memory_keyring.data == {}


def test_secret_never_reaches_the_file(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    text = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert SECRET not in text
    assert "OARUMI_API_TOKEN" in text  # the name is recorded, the value is not
    assert memory_keyring.data[("oarumi", "OARUMI_API_TOKEN")] == SECRET


def test_hint_names_are_secret_even_when_not_asked(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET, secret=False)
    assert SECRET not in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_custom_name_can_be_forced_to_secret(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_CUSTOM_THING", SECRET, secret=True)
    assert SECRET not in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_secret_entries_carry_no_value(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    entry = next(e for e in mgr.entries() if e.name == "OARUMI_API_TOKEN")
    assert entry.secret and entry.is_set
    assert entry.value is None
    assert SECRET not in repr(entry)
    assert mask(entry) == MASK


def test_unset_removes_secret_from_keychain_and_file(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    assert mgr.unset("OARUMI_API_TOKEN") is True
    assert memory_keyring.data == {}
    assert "OARUMI_API_TOKEN" not in (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert mgr.unset("OARUMI_API_TOKEN") is False


def test_apply_loads_values_without_overriding_the_shell(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    environ: dict[str, str] = {"OARUMI_LOG_LEVEL": "ERROR"}
    mgr = _manager(tmp_path, environ)
    mgr.set("OARUMI_LOG_LEVEL", "DEBUG")
    mgr.set("OARUMI_OFFLINE", "1")
    mgr.set("OARUMI_API_TOKEN", SECRET)

    report = mgr.apply()

    assert environ["OARUMI_LOG_LEVEL"] == "ERROR"  # shell wins
    assert environ["OARUMI_OFFLINE"] == "1"
    assert environ["OARUMI_API_TOKEN"] == SECRET
    assert set(report.applied) == {"OARUMI_OFFLINE", "OARUMI_API_TOKEN"}
    assert SECRET not in repr(report)


def test_apply_skips_secrets_when_keychain_is_missing(tmp_path: Path) -> None:
    environ: dict[str, str] = {}
    SettingsFile(tmp_path / "settings.json").save(StoredData(secrets={"OARUMI_API_TOKEN"}))
    mgr = _manager(tmp_path, environ)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(KeyringSecretStore, "get", _raise_unavailable)
        report = mgr.apply()
    assert report.skipped_secret == ("OARUMI_API_TOKEN",)
    assert "OARUMI_API_TOKEN" not in environ


def test_set_refuses_secret_without_writing_the_file(tmp_path: Path) -> None:
    mgr = _manager(tmp_path)
    previous = keyring.get_keyring()
    keyring.set_keyring(unusable_backend("null"))
    try:
        with pytest.raises(SecretBackendUnavailable):
            mgr.set("OARUMI_API_TOKEN", SECRET)
    finally:
        keyring.set_keyring(previous)
    assert not (tmp_path / "settings.json").exists()


def test_shell_only_variable_cannot_be_stored(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    with pytest.raises(ValueError, match="shell only"):
        _manager(tmp_path).set("OARUMI_CONFIG_DIR", str(tmp_path))


def test_invalid_name_is_rejected(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    with pytest.raises(ValueError, match="OARUMI_SOMETHING"):
        _manager(tmp_path).set("PATH", "/usr/bin")


def test_reveal_only_returns_stored_secrets(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    mgr.set("OARUMI_LOG_LEVEL", "INFO")
    assert mgr.reveal("OARUMI_API_TOKEN") == SECRET
    assert mgr.reveal("OARUMI_LOG_LEVEL") is None
    assert mgr.reveal("OARUMI_NEVER_SET") is None


def test_secret_values_feed_the_redaction_filter(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    assert mgr.secret_values() == [SECRET]


def test_entries_mark_shell_overrides(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _manager(tmp_path, {"OARUMI_LOG_LEVEL": "ERROR"})
    entry = next(e for e in mgr.entries() if e.name == "OARUMI_LOG_LEVEL")
    assert entry.overridden_by_shell


def test_corrupt_file_surfaces_as_settings_error(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text("{", encoding="utf-8")
    with pytest.raises(SettingsError):
        _manager(tmp_path).entries()


def _raise_unavailable(self: KeyringSecretStore, name: str) -> str | None:
    raise SecretBackendUnavailable("unavailable")


def test_entries_report_where_each_value_comes_from(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _manager(tmp_path, {"OARUMI_LOG_LEVEL": "ERROR"})
    mgr.set("OARUMI_OFFLINE", "1")
    rows = {e.name: e for e in mgr.entries()}
    assert rows["OARUMI_LOG_LEVEL"].source == "shell"
    assert rows["OARUMI_LOG_LEVEL"].effective == "ERROR"
    assert rows["OARUMI_OFFLINE"].source == "saved"
    assert rows["OARUMI_OFFLINE"].effective == "1"
    assert rows["OARUMI_DEV_MODELS"].source == "default"
    assert rows["OARUMI_DEV_MODELS"].effective == "1"


def test_values_loaded_at_startup_are_not_reported_as_shell_overrides(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    environ: dict[str, str] = {}
    mgr = _manager(tmp_path, environ)
    mgr.set("OARUMI_OFFLINE", "1")
    mgr.apply()  # copies the saved value into the environment
    row = next(e for e in mgr.entries() if e.name == "OARUMI_OFFLINE")
    assert not row.overridden_by_shell
    assert row.source == "saved"


def test_secret_entries_expose_source_but_never_the_value(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _manager(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    row = next(e for e in mgr.entries() if e.name == "OARUMI_API_TOKEN")
    assert row.source == "saved"
    assert row.effective is None


def test_backend_name_is_none_when_no_keychain_is_usable(tmp_path: Path) -> None:
    previous = keyring.get_keyring()
    keyring.set_keyring(unusable_backend("fail"))
    try:
        assert KeyringSecretStore().backend_name() is None
    finally:
        keyring.set_keyring(previous)


def test_backend_name_is_reported_when_a_keychain_is_usable(memory_keyring: MemoryKeyring) -> None:
    assert KeyringSecretStore().backend_name()
