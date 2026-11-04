#!/usr/bin/env bash
# Run Python + Kotlin parity runners and fail on any diff.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate || true

CORPUS="${1:-parity-basic}"
STRICT="${OARUMI_STRICT_PARITY:-1}"

echo "[parity] python ($CORPUS)"
python tools/parity_runner.py --corpus "$CORPUS" --strict --out /tmp/oarumi-python.json

echo "[parity] kotlin ($CORPUS)"
if [ -x android/gradlew ]; then
  (cd android && ./gradlew --quiet :engine:test --tests oarumi.ParityTest \
    -Poarumi.parity.corpus="$CORPUS")
  # ParityTest writes its own JUnit report; extracting got outputs requires
  # a helper. For now, rely on the JUnit XML + the Python-vs-gold comparison.
else
  echo "[parity] skipping kotlin (no gradlew)"
fi

echo "[parity] diff against gold"
python - <<'PY'
import json, sys
data = json.load(open("/tmp/oarumi-python.json"))
if data.get("failed", 0) > 0:
    print(f"PARITY FAIL: {data['failed']} of {data['total']}", file=sys.stderr)
    for c in data["cases"]:
        if c.get("match") is False:
            print(f"  {c['case_id']}: mismatch", file=sys.stderr)
    sys.exit(1)
print(f"PARITY OK: {data['passed']}/{data['total']}")
PY

if [ "$STRICT" = "1" ]; then
  python tools/parity_compare.py --python /tmp/oarumi-python.json --json
fi
