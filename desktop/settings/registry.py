"""The OARUMI_* variables the desktop app and CLI understand.

Only names matching ``NAME_RE`` can be stored, so typos and unrelated environment
variables are rejected. Any name containing a secret-looking word is stored as a
secret even if the caller does not ask for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

NAME_RE = re.compile(r"^OARUMI_[A-Z][A-Z0-9_]{0,63}$")
SECRET_NAME_HINT = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|KEY)")
MAX_VALUE_LENGTH = 4096

Kind = Literal["str", "bool", "int", "choice", "path", "secret"]


@dataclass(frozen=True)
class Variable:
    name: str
    kind: Kind
    description: str
    default: str = ""
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    shell_only: bool = False

    @property
    def secret(self) -> bool:
        return self.kind == "secret" or is_secret_name(self.name)


def is_secret_name(name: str) -> bool:
    return SECRET_NAME_HINT.search(name) is not None


REGISTRY: dict[str, Variable] = {
    v.name: v
    for v in (
        Variable(
            "OARUMI_HOME",
            "path",
            "Data root that holds the language DB and models. Defaults to the repo.",
        ),
        Variable(
            "OARUMI_STRICT_PARITY",
            "bool",
            "Treat any parity divergence as a test failure.",
            default="0",
        ),
        Variable(
            "OARUMI_DEV_MODELS",
            "bool",
            "Use development model stubs instead of full weights.",
            default="1",
        ),
        Variable(
            "OARUMI_LOG_LEVEL",
            "choice",
            "Logging verbosity.",
            default="INFO",
            choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        ),
        Variable(
            "OARUMI_OFFLINE",
            "bool",
            "Disable every network call (used by the offline test suite).",
            default="0",
        ),
        Variable(
            "OARUMI_PARITY_HOST",
            "str",
            "Bind address for the parity web GUI.",
            default="127.0.0.1",
        ),
        Variable(
            "OARUMI_PARITY_PORT",
            "int",
            "Port for the parity web GUI.",
            default="8090",
            minimum=1,
            maximum=65535,
        ),
        Variable(
            "OARUMI_DISABLE_AVATAR",
            "bool",
            "Hide the desktop avatar widget.",
            default="0",
        ),
        Variable(
            "OARUMI_CONFIG_DIR",
            "path",
            "Where settings.json is kept. Read from the shell only, never stored.",
            shell_only=True,
        ),
    )
}


def variable_for(name: str) -> Variable:
    """Return the registered variable, or a generic one for a custom name."""
    known = REGISTRY.get(name)
    if known is not None:
        return known
    kind: Kind = "secret" if is_secret_name(name) else "str"
    return Variable(name, kind, "Custom variable.")


def validate_value(var: Variable, value: str) -> str:
    """Return the value to store, or raise ValueError.

    Error messages never include the value, so a rejected secret cannot leak
    through a dialog, a log line or a traceback.
    """
    if not value:
        raise ValueError(f"{var.name}: value must not be empty")
    if len(value) > MAX_VALUE_LENGTH:
        raise ValueError(f"{var.name}: value is longer than {MAX_VALUE_LENGTH} characters")
    if any(ch in value for ch in ("\x00", "\n", "\r")):
        raise ValueError(f"{var.name}: value must be a single line with no NUL characters")
    if value != value.strip():
        raise ValueError(f"{var.name}: value has leading or trailing whitespace")

    if var.kind == "bool" and value not in ("0", "1"):
        raise ValueError(f"{var.name}: must be 0 or 1")
    if var.kind == "int":
        if not value.isdigit():
            raise ValueError(f"{var.name}: must be a whole number")
        number = int(value)
        if var.minimum is not None and number < var.minimum:
            raise ValueError(f"{var.name}: must be at least {var.minimum}")
        if var.maximum is not None and number > var.maximum:
            raise ValueError(f"{var.name}: must be at most {var.maximum}")
    if var.kind == "choice" and value not in var.choices:
        raise ValueError(f"{var.name}: must be one of {', '.join(var.choices)}")
    return value
