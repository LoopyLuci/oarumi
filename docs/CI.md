# CI — Continuous Integration

Every PR runs `ci.yml`; nightly runs `nightly.yml`; tag pushes run
`android-release.yml` (Batch 12). This document explains the matrix and how
to reproduce a failure locally.

---

## § 1. Job overview

### PR jobs (`ci.yml`)

| Job | What it verifies | Typical duration |
|---|---|---|
| `lint` | `ruff`, `black --check`, `mypy --strict` on `engine/python`, `desktop`, `tools` | 2 min |
| `docs` | Every markdown link in the repo resolves | 30 s |
| `schema` | No drift between `language/*.yaml` and `language/schemas/*.json` | 30 s |
| `unit` (3.11, 3.12) | `engine/python/tests`, `desktop/tests`, `tools/tests` with `--cov-fail-under=85` | 6 min |
| `parity` | `tests/parity` (basic corpus) with `OARUMI_STRICT_PARITY=1` | 5 min |
| `fault` | `tests/fault` — every shield trigger fires | 3 min |
| `offline` | `tests/offline` — zero network calls | 3 min |
| `android-unit` | `:engine:test`, `:app:testMlkitDebugUnitTest`, `:app:testArgosDebugUnitTest` | 15 min |
| `parity-web` | `tools/parity_web/tests` with `--cov-fail-under=85` | 4 min |
| `ci-pass` | Aggregates the above; required status check | 10 s |

### Nightly jobs (`nightly.yml`)

| Job | What it verifies |
|---|---|
| `complex-corpus` | `tests/parity --parity-corpus=parity-complex` (slow) |
| `chaos` | `tests/chaos` — recovery FSM under random triggers |
| `bench` | `tests/bench --benchmark-only` compared to `tests/bench/baseline.json` (20% tolerance) |
| `android-instrumented` | `:app:connectedMlkitDebugAndroidTest` on an emulator |
| `parity-web-e2e` | Start the parity web server, curl health, trigger a real run, fetch the diff |

---

## § 2. Reproduce a failure locally

Every CI job is reproducible locally by running the same commands.

### `lint` fails

```bash
ruff check .
black --check .
mypy --strict engine/python desktop tools
ruff check --fix .      # auto-fix if possible
black .                 # reformat
```

### `docs` fails

```bash
python -m pytest tools/tests/test_docs_links.py -q
```

The failure message names the file and the broken link target.

### `schema` fails

```bash
python tools/schema_export.py --check
```

If drift is intentional:
1. Update `language/schemas/*.json` to declare the new field.
2. Add a migration in `language/migrations/` if the DB schema changed.
3. Re-run `python tools/validate_schemas.py --all` and `python tools/seed_db.py`.

### `unit` fails

```bash
./scripts/ci_setup.sh
source .venv/bin/activate
pytest engine/python/tests desktop/tests tools/tests -q \
  --cov=oarumi --cov=desktop --cov=tools --cov-fail-under=85
```

### `parity` fails

```bash
source .venv/bin/activate
OARUMI_STRICT_PARITY=1 pytest tests/parity -q --parity-corpus=parity-basic
```

Read `tests/parity/README.md`. A parity failure is a **high-risk change** —
either the Python engine changed (and Kotlin must follow in the same PR) or
the frozen gold needs regeneration (`python tools/freeze_gold.py
--corpus parity-basic`, then review the diff).

### `fault` fails

```bash
source .venv/bin/activate
pytest tests/fault -q
```

Look for the trigger in `tests/parity/config.yaml#fault_triggers` — every
trigger must have a passing test. A failure here means the shield or FSM
regressed.

### `offline` fails

```bash
source .venv/bin/activate
pytest tests/offline -q -x
```

The `-x` stops at the first failure. The traceback shows the exact network
call that was attempted. Grep for `urllib`, `requests`, `http.client`,
`aiohttp`.

### `android-unit` fails

```bash
cd android
./gradlew --no-daemon :engine:test :app:testMlkitDebugUnitTest :app:testArgosDebugUnitTest
```

Test reports live at `android/engine/build/reports/tests/test/` and
`android/app/build/reports/tests/`.

### `parity-web` fails

```bash
python -m pytest tools/parity_web/tests -q --cov=tools.parity_web --cov-fail-under=85
```

---

## § 3. Nightly triage

Nightly failures are not PR-blocking but must be fixed within 48 hours.

### `bench` regression

Open `bench-report.json` and compare to `tests/bench/baseline.json`. A
regression is `current_mean_ms > baseline_mean_ms * 1.20`. To accept a new
baseline:

1. Confirm the regression is intentional (e.g., a new feature).
2. Replace `tests/bench/baseline.json` with the new means, reviewed line by
   line in the PR.
3. Note the change in `CHANGELOG.md`.

### `chaos` failure

The traceback shows the seeded random sequence. Reproduce with:

```bash
pytest tests/chaos -q -p no:cacheprovider
```

The `.oarumi-audit.jsonl` artifact contains the audit log from the failed
run. Look for the FSM transition sequence immediately before the assertion
fired.

### `android-instrumented` failure

Download `android-instrumented-reports` and open `index.html` in the
`connected/` subdirectory. It contains screenshots and logcat for failed
tests. Reproduce locally with a running emulator:

```bash
adb devices
cd android
./gradlew :app:connectedMlkitDebugAndroidTest
```

### `parity-web-e2e` failure

The server log is uploaded as `/tmp/parity-web.log`. Reproduce locally:

```bash
python -m tools.parity_web.server &
sleep 2
curl -sf http://127.0.0.1:8090/api/health
curl -sf -X POST http://127.0.0.1:8090/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"corpus":"parity-basic","targets":["python"]}'
```

---

## § 4. Caches and artifacts

| Cache | Key | Purpose |
|---|---|---|
| pip | `requirements-lock.txt` + `pyproject.toml` | Avoid reinstalling deps |
| Gradle | `~/.gradle/caches`, `~/.gradle/wrapper` | Avoid re-downloading Gradle distribution |
| Android emulator | Not cached | Emulator is provisioned per nightly run |

Artifacts uploaded per PR:

- `coverage-py{311,312}.xml` (from `unit`)
- `parity-py-failure/` (only on parity failure)
- `android-test-results/` (from `android-unit`)

Artifacts uploaded per nightly:

- `parity-complex-results/`
- `chaos-failure-artifacts/`
- `bench-report/`
- `android-instrumented-reports/`

Retention: 7 days for PR, 14–30 days for nightly.

---

## § 5. Adding a new CI job

1. If it runs on every PR, add it to `ci.yml` and to the `needs` list of
   `ci-pass`.
2. If it runs nightly, add it to `nightly.yml` and to the `needs` list of
   `nightly-pass`.
3. If it has a coverage floor, use `--cov-fail-under=<N>`. Never allow a job
   to pass without a coverage floor if it is testing Python code.
4. Update this document's § 1 table and § 2 reproduction section.
5. Update `HANDOVER.md` § 6 (runbooks) if the job corresponds to a release
   step.

---

## § 6. Secret management

| Secret | Used by | Rotation |
|---|---|---|
| `ANDROID_KEYSTORE_B64` | `android-release.yml` | Only with store coordination |
| `ANDROID_KEYSTORE_PASSWORD` | `android-release.yml` | Annually |
| `ANDROID_KEY_ALIAS` | `android-release.yml` | Never (keystore continuity) |
| `ANDROID_KEY_PASSWORD` | `android-release.yml` | Annually |
| `CODECOV_TOKEN` (optional) | None (coverage is uploaded as an artifact today) | N/A |

Secrets are provisioned at the org level. No CI job reads personal tokens.
