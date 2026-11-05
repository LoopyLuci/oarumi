"""The command-line interface: values come from stdin, never from argv."""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from desktop.settings.cli import EXIT_BAD_INPUT, EXIT_NO_KEYCHAIN, EXIT_OK, main
from desktop.settings.manager import EnvManager
from desktop.settings.store import KeyringSecretStore, SettingsFile
from desktop.tests.keyring_fake import MemoryKeyring, unusable_backend

SECRET = "cli-SECRET-value-99"


@pytest.fixture()
def memory_keyring() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


def _run(mgr: EnvManager, argv: list[str], stdin_text: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(
        argv,
        manager=mgr,
        stdin=io.StringIO(stdin_text),
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


def _mgr(tmp_path: Path) -> EnvManager:
    return EnvManager(KeyringSecretStore(), SettingsFile(tmp_path / "settings.json"), {})


def test_set_secret_reads_value_from_stdin_and_hides_it(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    mgr = _mgr(tmp_path)
    code, out, err = _run(mgr, ["set", "OARUMI_API_TOKEN"], stdin_text=SECRET + "\n")
    assert code == EXIT_OK
    assert SECRET not in out + err
    assert memory_keyring.data[("oarumi", "OARUMI_API_TOKEN")] == SECRET
    assert SECRET not in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_list_masks_secrets(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _mgr(tmp_path)
    mgr.set("OARUMI_API_TOKEN", SECRET)
    mgr.set("OARUMI_LOG_LEVEL", "DEBUG")
    code, out, _ = _run(mgr, ["list"])
    assert code == EXIT_OK
    assert SECRET not in out
    assert "DEBUG" in out
    assert "OARUMI_API_TOKEN" in out


def test_invalid_name_exits_two_without_echoing_a_value(
    tmp_path: Path, memory_keyring: MemoryKeyring
) -> None:
    code, out, err = _run(_mgr(tmp_path), ["set", "PATH"], stdin_text=SECRET)
    assert code == EXIT_BAD_INPUT
    assert SECRET not in out + err
    assert "OARUMI_SOMETHING" in err


def test_unavailable_keychain_exits_three(tmp_path: Path) -> None:
    previous = keyring.get_keyring()
    keyring.set_keyring(unusable_backend("fail"))
    try:
        code, _, err = _run(_mgr(tmp_path), ["set", "OARUMI_API_TOKEN"], stdin_text=SECRET)
    finally:
        keyring.set_keyring(previous)
    assert code == EXIT_NO_KEYCHAIN
    assert SECRET not in err


def test_unset_reports_both_outcomes(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _mgr(tmp_path)
    mgr.set("OARUMI_LOG_LEVEL", "INFO")
    _, out, _ = _run(mgr, ["unset", "OARUMI_LOG_LEVEL"])
    assert "removed OARUMI_LOG_LEVEL" in out
    _, out, _ = _run(mgr, ["unset", "OARUMI_LOG_LEVEL"])
    assert "was not stored" in out


def test_plain_value_from_stdin_is_stored(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    mgr = _mgr(tmp_path)
    code, out, _ = _run(mgr, ["set", "OARUMI_LOG_LEVEL"], stdin_text="WARNING\n")
    assert code == EXIT_OK
    assert "value stored" in out
    assert any(e.value == "WARNING" for e in mgr.entries() if e.name == "OARUMI_LOG_LEVEL")
