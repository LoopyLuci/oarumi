"""Allow `python -m tools <subcommand>` as a synonym for `oarumi <subcommand>`."""

from __future__ import annotations

import sys

from tools.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
