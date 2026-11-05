"""Storage for the settings manager.

Secret values live only in the OS keychain. Everything else lives in a JSON
file in the user's config directory, outside the repository. That file never
holds a secret value, only the names of the secrets.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import keyring
from keyring.backends import fail, null
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE = "oarumi"
SETTINGS_VERSION = 1


class SettingsError(Exception):
    """The settings file is unreadable or has an unexpected shape."""


class SecretBackendUnavailable(RuntimeError):
    """No usable OS keychain. Secrets are refused rather than written to disk."""


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...

    def backend_name(self) -> str | None: ...


# Keyring backend class names, mapped to the names people recognise.
_BACKEND_LABELS = (
    ("winvault", "Windows Credential Manager"),
    ("macos", "macOS Keychain"),
    ("secretservice", "Secret Service (GNOME Keyring)"),
    ("kwallet", "KWallet (KDE)"),
)


class KeyringSecretStore:
    """Secrets in the OS keychain, under the service name ``oarumi``."""

    def __init__(self, service: str = SERVICE) -> None:
        self._service = service

    def backend_name(self) -> str | None:
        """Human name of the usable keychain, or None when there is none."""
        backend = keyring.get_keyring()
        if isinstance(backend, (fail.Keyring, null.Keyring)):
            return None
        label = f"{type(backend).__module__}.{type(backend).__name__}".lower()
        for needle, name in _BACKEND_LABELS:
            if needle in label:
                return name
        return type(backend).__name__

    def _ensure_backend(self) -> None:
        backend = keyring.get_keyring()
        if isinstance(backend, (fail.Keyring, null.Keyring)):
            raise SecretBackendUnavailable(
                "No usable OS keychain was found (Windows Credential Manager, "
                "macOS Keychain or Secret Service). Oarumi will not store secrets "
                "in a plain file."
            )

    def get(self, name: str) -> str | None:
        self._ensure_backend()
        try:
            return keyring.get_password(self._service, name)
        except KeyringError as exc:
            # Type name only: the keyring message must not be echoed.
            raise SecretBackendUnavailable(f"keychain read failed ({type(exc).__name__})") from None

    def set(self, name: str, value: str) -> None:
        self._ensure_backend()
        try:
            keyring.set_password(self._service, name, value)
        except KeyringError as exc:
            raise SecretBackendUnavailable(
                f"keychain write failed ({type(exc).__name__})"
            ) from None

    def delete(self, name: str) -> None:
        self._ensure_backend()
        try:
            keyring.delete_password(self._service, name)
        except PasswordDeleteError:
            return  # already absent
        except KeyringError as exc:
            raise SecretBackendUnavailable(
                f"keychain delete failed ({type(exc).__name__})"
            ) from None


@dataclass
class StoredData:
    values: dict[str, str] = field(default_factory=dict)
    secrets: set[str] = field(default_factory=set)


class SettingsFile:
    """Atomic JSON storage for non-secret values and the list of secret names."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> StoredData:
        if not self.path.exists():
            return StoredData()
        try:
            raw: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SettingsError(f"cannot read {self.path.name}: {type(exc).__name__}") from None
        if not isinstance(raw, dict):
            raise SettingsError(f"{self.path.name} has an unexpected shape")
        values = raw.get("values", {})
        secrets = raw.get("secrets", [])
        if not isinstance(values, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in values.items()
        ):
            raise SettingsError(f"{self.path.name}: 'values' must map names to strings")
        if not isinstance(secrets, list) or not all(isinstance(s, str) for s in secrets):
            raise SettingsError(f"{self.path.name}: 'secrets' must be a list of names")
        return StoredData(values=dict(values), secrets=set(secrets))

    def save(self, data: StoredData) -> None:
        overlap = data.secrets & set(data.values)
        if overlap:
            raise SettingsError("refusing to write a secret name into the plain values")
        payload = {
            "version": SETTINGS_VERSION,
            "values": dict(sorted(data.values.items())),
            "secrets": sorted(data.secrets),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if os.name == "posix":
            os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
