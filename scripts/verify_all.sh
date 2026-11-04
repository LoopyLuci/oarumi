#!/usr/bin/env bash
# Oarumi verification. Must pass before any PR merges.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  for _act in .venv/bin/activate .venv/Scripts/activate; do
  if [ -f "$_act" ]; then source "$_act"; break; fi
done
fi

STRICT="${OARUMI_STRICT_PARITY:-0}"

echo "[verify] ruff";            ruff check .
echo "[verify] black --check";   black --check .
echo "[verify] mypy";            mypy --strict engine/python desktop tools
echo "[verify] schemas";         python tools/validate_schemas.py --all
echo "[verify] primes";          python tools/validate_primes.py

if [ -d tests/unit ]; then
  echo "[verify] unit + contract + integration"
  python -m pytest tests/unit tests/contract tests/integration -q || exit 1
fi

if [ -d tests/parity ]; then
  echo "[verify] parity (strict=$STRICT)"
  OARUMI_STRICT_PARITY="$STRICT" python -m pytest tests/parity -q || exit 1
fi

if [ -d tests/fault ]; then
  echo "[verify] fault injection"; python -m pytest tests/fault -q || exit 1
fi

if [ -d tests/offline ]; then
  echo "[verify] offline";         python -m pytest tests/offline -q || exit 1
fi

if [ -x android/gradlew ]; then
  echo "[verify] android lint + unit"
  (cd android && ./gradlew --quiet ktlintCheck :engine:test :app:testMlkitDebugUnitTest :app:testArgosDebugUnitTest)
fi

if [ -f tools/tests/test_docs_links.py ]; then
  echo "[verify] docs links";       python -m pytest tools/tests/test_docs_links.py -q || exit 1
fi

if [ -f tools/schema_export.py ]; then
  echo "[verify] schema drift";     python tools/schema_export.py --check || exit 1
fi

echo "[verify] all checks passed"
