"""``python -m desktop.settings``: CLI when given arguments, otherwise the app on the Settings tab."""

from __future__ import annotations

import sys


def _gui() -> int:
    from desktop.app import main

    return main(["oarumi"], start_tab="Settings")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        from desktop.settings.cli import main

        raise SystemExit(main(sys.argv[1:]))
    raise SystemExit(_gui())
