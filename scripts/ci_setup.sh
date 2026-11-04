#!/usr/bin/env bash
# Shared setup step for all CI jobs. Idempotent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "[ci-setup] python=$($PYTHON --version)"
$PYTHON -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[dev]"

echo "[ci-setup] bootstrapping language DB and audio assets"
./scripts/bootstrap.sh
if [ ! -f assets/audio/manifest.json ] || \
   [ "$(python -c 'import json; print(sum(1 for a in json.load(open("assets/audio/manifest.json"))["assets"] if a["sha256"]))')" = "0" ]; then
  python tools/generate_audio_assets.py
fi

echo "[ci-setup] regenerating dev-stub hashes"
python tools/fetch_dev_stubs.py --regenerate-hashes >/dev/null

echo "[ci-setup] generating parity corpora"
if [ ! -d tests/parity/data/parity-basic ]; then
  python tools/generate_parity_corpus.py
fi
if [ ! -d tests/parity/data/parity-complex ]; then
  python tools/generate_parity_complex.py
fi

echo "[ci-setup] freezing gold (idempotent)"
python tools/freeze_gold.py --corpus parity-basic || true
python tools/freeze_gold.py --corpus parity-complex || true
python tools/freeze_renderer_gold.py || true

echo "[ci-setup] done"
