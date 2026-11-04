"""Entry point: `oarumi-parity` or `python -m tools.parity_web.server`.

Binds to 127.0.0.1:8090 by default. Override with OARUMI_PARITY_HOST and
OARUMI_PARITY_PORT.
"""

from __future__ import annotations

import os
import sys

import uvicorn

from tools.parity_web.api import create_app


def main(argv: list[str] | None = None) -> int:
    del argv  # uvicorn owns CLI parsing here
    host = os.environ.get("OARUMI_PARITY_HOST", "127.0.0.1")
    port = int(os.environ.get("OARUMI_PARITY_PORT", "8090"))
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
