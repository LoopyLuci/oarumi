"""Keychain adapter and the plain settings file."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from desktop.settings.store import (
    KeyringSecretStore,
    SecretBackendUnavailable,
    SettingsError,
    SettingsFile,
    StoredData,
)
from desktop.tests.keyring_fake import MemoryKeyring, unusable_backend


@pytest.fixture()
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


def test_keyring_store_round_trip(memory_keyring: MemoryKeyring) -> None:
    store = KeyringSecretStore()
    store.set("OARUMI_API_TOKEN", "abc123")
    assert store.get("OARUMI_API_TOKEN") == "abc123"
    store.delete("OARUMI_API_TOKEN")
    assert store.get("OARUMI_API_TOKEN") is None


def test_deleting_an_absent_secret_is_not_an_error(memory_keyring: MemoryKeyring) -> None:
    KeyringSecretStore().delete("OARUMI_NEVER_SET")


@pytest.mark.parametrize("kind", ["fail", "null"])
def test_unusable_keychain_is_refused_with_no_plaintext_fallback(kind: str) -> None:
    previous = keyring.get_keyring()
    keyring.set_keyring(unusable_backend(kind))
    try:
        store = KeyringSecretStore()
        with pytest.raises(SecretBackendUnavailable, match="will not store secrets"):
            store.set("OARUMI_API_TOKEN", "abc123")
        with pytest.raises(SecretBackendUnavailable):
            store.get("OARUMI_API_TOKEN")
    finally:
        keyring.set_keyring(previous)


def test_settings_file_missing_loads_empty(tmp_path: Path) -> None:
    data = SettingsFile(tmp_path / "settings.json").load()
    assert data == StoredData()


def test_settings_file_round_trip_and_no_temp_file_left(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    file = SettingsFile(path)
    file.save(StoredData(values={"OARUMI_LOG_LEVEL": "DEBUG"}, secrets={"OARUMI_API_TOKEN"}))

    loaded = file.load()
    assert loaded.values == {"OARUMI_LOG_LEVEL": "DEBUG"}
    assert loaded.secrets == {"OARUMI_API_TOKEN"}
    assert not (tmp_path / "settings.json.tmp").exists()


def test_settings_file_refuses_a_name_in_both_maps(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="refusing"):
        SettingsFile(tmp_path / "s.json").save(
            StoredData(values={"OARUMI_X_TOKEN": "v"}, secrets={"OARUMI_X_TOKEN"})
        )


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[1, 2]",
        '{"values": {"OARUMI_A": 3}}',
        '{"secrets": "OARUMI_A"}',
    ],
)
def test_malformed_settings_file_raises_settings_error(tmp_path: Path, content: str) -> None:
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SettingsError):
        SettingsFile(path).load()


def test_saved_file_contains_names_but_only_plain_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    SettingsFile(path).save(StoredData(values={"OARUMI_LOG_LEVEL": "INFO"}, secrets={"OARUMI_T"}))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["secrets"] == ["OARUMI_T"]
    assert "OARUMI_T" not in payload["values"]
