"""The settings manager: the only code that reads or writes stored variables.

The GUI, the CLI and app startup all go through ``EnvManager``. Its ``Entry``
objects carry no value for a secret, so a listing cannot leak one by accident.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

from desktop.settings.registry import NAME_RE, REGISTRY, validate_value, variable_for
from desktop.settings.store import (
    KeyringSecretStore,
    SecretBackendUnavailable,
    SecretStore,
    SettingsFile,
)

MASK = "********"
CONFIG_FILE = "settings.json"


@dataclass(frozen=True)
class Entry:
    name: str
    kind: str
    description: str
    secret: bool
    is_set: bool
    overridden_by_shell: bool
    value: str | None = None  # always None for a secret


@dataclass(frozen=True)
class ApplyReport:
    """Names only. Values are never part of the report."""

    applied: tuple[str, ...] = ()
    skipped_secret: tuple[str, ...] = ()


class EnvManager:
    def __init__(
        self,
        secrets: SecretStore,
        file: SettingsFile,
        environ: MutableMapping[str, str] | None = None,
    ) -> None:
        self._secrets = secrets
        self._file = file
        self._environ: MutableMapping[str, str] = os.environ if environ is None else environ

    # --- writes -------------------------------------------------------------

    def set(self, name: str, value: str, *, secret: bool = False) -> None:
        """Store a variable. ``secret=True`` forces keychain storage for any name."""
        if not NAME_RE.match(name):
            raise ValueError("names must look like OARUMI_SOMETHING (A-Z, 0-9, underscore)")
        var = variable_for(name)
        if var.shell_only:
            raise ValueError(f"{name} is read from the shell only and cannot be stored")
        clean = validate_value(var, value)
        # Hint-matching names are always secrets, even if the caller passes False.
        is_secret = var.secret or secret

        data = self._file.load()
        if is_secret:
            self._secrets.set(name, clean)  # fails before the file changes
            data.values.pop(name, None)
            data.secrets.add(name)
        else:
            data.values[name] = clean
        self._file.save(data)

    def unset(self, name: str) -> bool:
        """Remove a stored variable. Returns False when nothing was stored."""
        data = self._file.load()
        was_secret = name in data.secrets
        if not was_secret and name not in data.values:
            return False
        if was_secret:
            self._secrets.delete(name)
            data.secrets.discard(name)
        data.values.pop(name, None)
        self._file.save(data)
        return True

    # --- reads --------------------------------------------------------------

    def entries(self) -> list[Entry]:
        """Every registered name plus every stored name. Secret values are omitted."""
        data = self._file.load()
        names = sorted(set(REGISTRY) | set(data.values) | data.secrets)
        rows: list[Entry] = []
        for name in names:
            var = variable_for(name)
            secret = var.secret or name in data.secrets
            is_set = name in data.secrets or name in data.values
            rows.append(
                Entry(
                    name=name,
                    kind="secret" if secret else var.kind,
                    description=var.description,
                    secret=secret,
                    is_set=is_set,
                    overridden_by_shell=name in self._environ,
                    value=None if secret else data.values.get(name),
                )
            )
        return rows

    def reveal(self, name: str) -> str | None:
        """Return a secret's value. Call only in response to an explicit user action."""
        if name not in self._file.load().secrets:
            return None
        return self._secrets.get(name)

    # --- startup ------------------------------------------------------------

    def apply(self) -> ApplyReport:
        """Load stored values into the environment. Shell variables always win."""
        data = self._file.load()
        applied: list[str] = []
        skipped: list[str] = []
        for name in sorted(data.values):
            if name not in self._environ:
                self._environ[name] = data.values[name]
                applied.append(name)
        for name in sorted(data.secrets):
            if name in self._environ:
                continue
            try:
                value = self._secrets.get(name)
            except SecretBackendUnavailable:
                skipped.append(name)
                continue
            if value is not None:
                self._environ[name] = value
                applied.append(name)
        return ApplyReport(applied=tuple(applied), skipped_secret=tuple(skipped))

    def secret_values(self) -> list[str]:
        """Current secret values, for the log redaction filter. Never logged."""
        values: list[str] = []
        for name in sorted(self._file.load().secrets):
            try:
                value = self._secrets.get(name)
            except SecretBackendUnavailable:
                continue
            if value:
                values.append(value)
        return values


def mask(entry: Entry) -> str:
    """Display text for a value: masked for secrets, plain otherwise."""
    if entry.secret:
        return MASK if entry.is_set else "(not set)"
    if entry.value is not None:
        return entry.value
    return "(not set)"


def default_settings_dir() -> Path:
    override = os.environ.get("OARUMI_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        root = Path(base) if base else Path.home() / ".config"
    return root / "oarumi"


def default_manager(environ: MutableMapping[str, str] | None = None) -> EnvManager:
    return EnvManager(
        KeyringSecretStore(),
        SettingsFile(default_settings_dir() / CONFIG_FILE),
        environ,
    )
