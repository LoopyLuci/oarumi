#!/usr/bin/env bash
# Run the Python and Kotlin reliability fixture tests and fail if either diverges.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate || true

echo "[parity-reliability] python"
python -m pytest engine/python/tests/test_shield.py engine/python/tests/test_intent_router.py -q

echo "[parity-reliability] kotlin"
(cd android && ./gradlew --quiet :engine:test --tests oarumi.reliability.CrossLanguageShieldTest)

echo "[parity-reliability] ok"
