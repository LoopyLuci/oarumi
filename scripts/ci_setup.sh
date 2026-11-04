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
# WAVs are gitignored while manifest.json is committed, so a fresh clone can
# have hashes but no files. Regenerate unless every listed asset is on disk.
if ! python -c 'import json, pathlib, sys
m = json.load(open("assets/audio/manifest.json"))
d = pathlib.Path("assets/audio")
sys.exit(0 if all(a["sha256"] and (d / a["path"]).exists() for a in m["assets"]) else 1)'; then
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
python tools/freeze_gold.py --corpus parity-basic
python tools/freeze_gold.py --corpus parity-complex
python tools/freeze_renderer_gold.py

echo "[ci-setup] done"
