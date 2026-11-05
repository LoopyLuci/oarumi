"""Command-line access to the settings manager.

    python -m desktop.settings list
    python -m desktop.settings set OARUMI_LOG_LEVEL DEBUG
    python -m desktop.settings set OARUMI_API_TOKEN          # prompts, hidden input
    printf '%s' "$VALUE" | python -m desktop.settings set OARUMI_API_TOKEN
    python -m desktop.settings unset OARUMI_API_TOKEN

Values are never taken from argv, so they do not appear in shell history or in
the process list.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from typing import TextIO

from desktop.settings.manager import EnvManager, default_manager, mask
from desktop.settings.registry import is_secret_name
from desktop.settings.store import SecretBackendUnavailable, SettingsError

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_NO_KEYCHAIN = 3


def _read_value(name: str, stdin: TextIO) -> str:
    if stdin.isatty():
        return getpass.getpass(f"Value for {name} (input hidden): ")
    return stdin.read().rstrip("\n")


def main(
    argv: list[str] | None = None,
    *,
    manager: EnvManager | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m desktop.settings")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="show every variable; secrets stay masked")
    set_cmd = commands.add_parser("set", help="store a variable (value is read securely)")
    set_cmd.add_argument("name")
    set_cmd.add_argument(
        "--secret",
        action="store_true",
        help="store in the OS keychain even if the name does not look secret",
    )
    unset_cmd = commands.add_parser("unset", help="remove a stored variable")
    unset_cmd.add_argument("name")
    args = parser.parse_args(argv)

    out = stdout or sys.stdout
    err = stderr or sys.stderr
    mgr = manager or default_manager()

    try:
        if args.command == "list":
            for entry in mgr.entries():
                status = "set" if entry.is_set else "not set"
                if entry.overridden_by_shell:
                    status += ", overridden by shell"
                print(f"{entry.name:<26} {status:<28} {mask(entry)}", file=out)
            return EXIT_OK

        if args.command == "set":
            value = _read_value(args.name, stdin or sys.stdin)
            mgr.set(args.name, value, secret=args.secret)
            secret = is_secret_name(args.name) or args.secret
            label = "secret, value hidden" if secret else "value stored"
            print(f"stored {args.name} ({label})", file=out)
            return EXIT_OK

        removed = mgr.unset(args.name)
        print(f"removed {args.name}" if removed else f"{args.name} was not stored", file=out)
        return EXIT_OK
    except ValueError as exc:
        print(f"error: {exc}", file=err)
        return EXIT_BAD_INPUT
    except SecretBackendUnavailable as exc:
        print(f"error: {exc}", file=err)
        return EXIT_NO_KEYCHAIN
    except SettingsError as exc:
        print(f"error: {exc}", file=err)
        return EXIT_BAD_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
