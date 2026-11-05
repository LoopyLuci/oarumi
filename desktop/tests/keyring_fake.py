"""An in-memory keyring backend, so tests use the real keyring API safely."""

from __future__ import annotations

from typing import Any, cast

from keyring.backend import KeyringBackend
from keyring.backends import fail, null
from keyring.errors import PasswordDeleteError


def unusable_backend(kind: str) -> KeyringBackend:
    """A keyring backend that stores nothing: ``fail`` raises, ``null`` drops values."""
    module: Any = fail if kind == "fail" else null
    return cast(KeyringBackend, module.Keyring())


class MemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        self.data: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.data[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.data.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) not in self.data:
            raise PasswordDeleteError("not found")
        del self.data[(service, username)]
