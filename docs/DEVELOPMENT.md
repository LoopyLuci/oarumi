# Development Setup

## Prerequisites

- Python 3.11+
- JDK 17 + Android SDK (for Android)
- `git`, `sqlite3`, `ffmpeg`
- ~2 GB free disk (dev-time model stubs)

## One-shot setup

```bash
./scripts/bootstrap.sh
```

This will:
1. Create a Python venv in `.venv/`.
2. Install Python deps from `pyproject.toml`.
3. Seed `language/oarumi.db` from `language/schema.sql` + data files.
4. Download dev-time model stubs to `models/dev-stubs/` (small, not the full stack).
5. Install git hooks (`python -m tools.ci --install-hooks`).
6. Install Android SDK components if `ANDROID_HOME` is set.

## Daily commands

```bash
python -m tools.ci --mode full        # preflight, lint, types, tests, parity, Android
python -m tools.ci --list          # every step and the modes that run it
python -m desktop.app              # desktop app
python -m pytest tests/unit -q     # fast unit tests only
cd android && ./gradlew :app:test  # Android unit tests
python -m tools.cli --help            # CLI surface
```

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `OARUMI_HOME` | Data dir for DB and models | repo root |
| `OARUMI_STRICT_PARITY` | Treat parity divergence as failure | `0` |
| `OARUMI_DEV_MODELS` | Use dev stubs instead of full models | `1` |
| `OARUMI_LOG_LEVEL` | Logging verbosity | `INFO` |

## Troubleshooting

- **`bootstrap.sh` fails on SQLite seed**: delete `language/oarumi.db` and re-run.
- **Android build fails on JDK**: ensure `JAVA_HOME` points at JDK 17.
- **Parity tests fail after pulling**: re-run `bootstrap.sh` — data files may have changed.
- **Old `omnilingua.db` still present after rename**: delete it; the app reads `oarumi.db` only.
