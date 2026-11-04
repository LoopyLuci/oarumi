#!/usr/bin/env bash
# Compatibility wrapper. The gate lives in tools/ci.py; this runs its full mode.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="python"
for candidate in .venv/bin/python .venv/Scripts/python.exe; do
  if [ -x "$candidate" ]; then PY="$candidate"; break; fi
done
exec "$PY" -m tools.ci --mode full "$@"
