#!/usr/bin/env bash
# Oarumi bootstrap — idempotent developer setup.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[oarumi] bootstrapping in $ROOT"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
for _act in .venv/bin/activate .venv/Scripts/activate; do
  if [ -f "$_act" ]; then source "$_act"; break; fi
done

echo "[oarumi] installing python deps"
pip install --upgrade pip >/dev/null
pip install -e ".[dev]"

DB="language/oarumi.db"
if [ ! -f "$DB" ]; then
  echo "[oarumi] seeding $DB"
  python tools/migrate.py --db "$DB" --apply
  python tools/seed_db.py --db "$DB"
else
  echo "[oarumi] $DB exists, applying any pending migrations"
  python tools/migrate.py --db "$DB" --apply
fi

if [ ! -f assets/audio/manifest.json ] ||    [ "$(python -c 'import json,sys; print(sum(1 for a in json.load(open("assets/audio/manifest.json"))["assets"] if a["sha256"]))')" = "0" ]; then
  echo "[oarumi] generating audio assets"
  python tools/generate_audio_assets.py ||     echo "[oarumi] WARN: audio asset generation failed; continuing"
else
  echo "[oarumi] audio assets present"
fi

if [ ! -d models/dev-stubs ]; then
  echo "[oarumi] fetching dev model stubs"
  python tools/fetch_dev_stubs.py --dest models/dev-stubs || \
    echo "[oarumi] WARN: could not fetch dev stubs (offline?); continuing"
fi

if [ -d .git ]; then
  cp scripts/hooks/pre-commit .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
  echo "[oarumi] installed git pre-commit hook"
fi

if [ -n "${ANDROID_HOME:-}" ]; then
  echo "[oarumi] ANDROID_HOME=$ANDROID_HOME"
else
  echo "[oarumi] ANDROID_HOME not set; skipping Android setup"
fi

echo "[oarumi] done. Try: python -m desktop.app"
