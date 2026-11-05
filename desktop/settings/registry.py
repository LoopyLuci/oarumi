"""The OARUMI_* variables the desktop app and CLI understand.

Only names matching ``NAME_RE`` can be stored, so typos and unrelated environment
variables are rejected. Any name containing a secret-looking word is stored as a
secret even if the caller does not ask for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

NAME_RE = re.compile(r"^OARUMI_[A-Z][A-Z0-9_]{0,63}$")
SECRET_NAME_HINT = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|KEY)")
MAX_VALUE_LENGTH = 4096

Kind = Literal["str", "bool", "int", "choice", "path", "secret"]
# When a changed value takes effect: at once, after Oarumi restarts, or the next
# time the tool that reads it starts.
Apply = Literal["now", "restart", "next run"]

ENGINE_GROUP = "Engine & data"
LOGGING_GROUP = "Logging"
INTERFACE_GROUP = "Interface"
PARITY_GROUP = "Parity tool"
ADVANCED_GROUP = "Advanced"
SECRETS_GROUP = "Secrets"
CUSTOM_GROUP = "Custom"

# Sidebar order in the Settings tab. Secrets and custom variables come last.
GROUPS: tuple[str, ...] = (
    ENGINE_GROUP,
    LOGGING_GROUP,
    INTERFACE_GROUP,
    PARITY_GROUP,
    ADVANCED_GROUP,
    SECRETS_GROUP,
    CUSTOM_GROUP,
)


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
    title: str = ""
    group: str = CUSTOM_GROUP
    apply: Apply = "restart"

    @property
    def secret(self) -> bool:
        return self.kind == "secret" or is_secret_name(self.name)

    @property
    def label(self) -> str:
        return self.title or self.name


def is_secret_name(name: str) -> bool:
    return SECRET_NAME_HINT.search(name) is not None


REGISTRY: dict[str, Variable] = {
    v.name: v
    for v in (
        Variable(
            "OARUMI_HOME",
            "path",
            "Folder that holds the language database and models. "
            "Leave unset to use the Oarumi project folder.",
            title="Data folder",
            group=ENGINE_GROUP,
        ),
        Variable(
            "OARUMI_DEV_MODELS",
            "bool",
            "Use lightweight development stubs instead of the full model weights.",
            default="1",
            title="Development model stubs",
            group=ENGINE_GROUP,
        ),
        Variable(
            "OARUMI_STRICT_PARITY",
            "bool",
            "Treat any parity divergence as a test failure.",
            default="0",
            title="Strict parity",
            group=ENGINE_GROUP,
        ),
        Variable(
            "OARUMI_OFFLINE",
            "bool",
            "Block every network call. The status bar shows the mode Oarumi started in.",
            default="0",
            title="Offline mode",
            group=ENGINE_GROUP,
        ),
        Variable(
            "OARUMI_LOG_LEVEL",
            "choice",
            "How much Oarumi writes to its log.",
            default="INFO",
            choices=("DEBUG", "INFO", "WARNING", "ERROR"),
            title="Log level",
            group=LOGGING_GROUP,
            apply="now",
        ),
        Variable(
            "OARUMI_DISABLE_AVATAR",
            "bool",
            "Hide the 3D avatar on the Sign tab. Useful on machines without WebEngine.",
            default="0",
            title="Hide 3D avatar",
            group=INTERFACE_GROUP,
        ),
        Variable(
            "OARUMI_PARITY_HOST",
            "str",
            "Address the parity web GUI listens on. Keep 127.0.0.1 unless you need more.",
            default="127.0.0.1",
            title="Parity web host",
            group=PARITY_GROUP,
            apply="next run",
        ),
        Variable(
            "OARUMI_PARITY_PORT",
            "int",
            "Port the parity web GUI listens on.",
            default="8090",
            minimum=1,
            maximum=65535,
            title="Parity web port",
            group=PARITY_GROUP,
            apply="next run",
        ),
        Variable(
            "OARUMI_CONFIG_DIR",
            "path",
            "Folder that holds settings.json. Read from the shell only, so it cannot be "
            "saved here.",
            shell_only=True,
            title="Settings folder",
            group=ADVANCED_GROUP,
        ),
    )
}


def variable_for(name: str) -> Variable:
    """Return the registered variable, or a generic one for a custom name."""
    known = REGISTRY.get(name)
    if known is not None:
        return known
    if is_secret_name(name):
        return Variable(name, "secret", "Custom secret.", group=SECRETS_GROUP)
    return Variable(name, "str", "Custom variable.")


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
    if var.kind == "path" and not Path(value).expanduser().is_dir():
        raise ValueError(f"{var.name}: folder does not exist")
    return value
