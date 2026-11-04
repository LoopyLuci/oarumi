"""cli.main maps Ctrl-C during a subcommand to exit status 130."""

from __future__ import annotations

import pytest

from tools import cli


def test_keyboard_interrupt_returns_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupted(args: object, ctx: object) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_cmd_validate", interrupted)
    assert cli.main(["validate"]) == 130
