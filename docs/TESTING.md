# Testing Strategy

> **Audience:** contributors adding tests; agents verifying changes.

---

## 1. Test layers

| Layer | Directory | What it proves | Runtime |
|---|---|---|---|
| **Unit** | `tests/unit/` | Individual functions are correct | seconds |
| **Contract** | `tests/contract/` | Engine interfaces match their spec | seconds |
| **Integration** | `tests/integration/` | Full pipeline end-to-end | minutes |
| **Parity** | `tests/parity/` | Neural path ≡ deterministic fallback within contract | minutes |
| **Fault injection** | `tests/fault/` | Failover triggers fire | minutes |
| **Offline** | `tests/offline/` | No network calls in the pipeline | minutes |
| **Chaos** | `tests/chaos/` | Recovery state machine behaves under stress | slow, nightly |
| **Bench** | `tests/bench/` | Latency and memory budgets | nightly |

## 2. Parity tests in detail

A parity test is a frozen set of inputs with two expected outputs:

1. The **gold** output from the deterministic path (frozen at Phase 1).
2. The **contract** bounds for the neural path (coverage, latency, validity).

The test passes if the neural path stays within the contract **or** the
deterministic fallback produces the gold output. With
`OARUMI_STRICT_PARITY=1`, any contract violation is a failure.

Data lives in `tests/parity/data/<component>/`. Gold outputs are generated
by `tools/freeze_gold.py` and must be regenerated when the language spec
changes (this is a high-risk change).

## 3. Fault injection

For each neural component, the suite:

1. Disables the neural path entirely → fallback must produce gold.
2. Corrupts the model file → integrity failure must trigger fallback.
3. Injects 10× latency → latency breach must trigger fallback.
4. Starves memory → resource trigger must fire.
5. Feeds adversarial input → validator must reject and fall back.

Exit criterion: **100% failover trigger rate** across the component's test set.

## 4. Offline tests

`tests/offline/conftest.py` monkeypatches `socket`, `requests`, and
`urllib` to raise on any call. The full pipeline is then exercised on a
small corpus. Any network attempt is a test failure.

## 5. Commands

```bash
./scripts/verify_all.sh                    # everything, warnings allowed
OARUMI_STRICT_PARITY=1 ./scripts/verify_all.sh   # CI mode, strict
python -m pytest tests/parity -q           # parity only
python -m pytest tests/fault -q            # fault injection only
python -m pytest tests/offline -q          # offline only
python -m pytest tests/bench --benchmark-only  # benchmarks
```

## 6. CI matrix

| Job | Runs on | Trigger |
|---|---|---|
| `lint` | PR | ruff, mypy, ktlint |
| `unit` | PR | Python + Kotlin |
| `parity` | PR | strict parity |
| `offline` | PR | network-stubbed pipeline |
| `fault` | PR | fault injection |
| `chaos` | nightly | recovery stress |
| `bench` | nightly | latency/memory budgets |
| `android-instrumented` | nightly | emulator tests |

## 7. Adding a test

1. Put it in the right layer directory.
2. If it is a parity test, add data to `tests/parity/data/` and update
   `tests/parity/config.yaml`.
3. If it exercises a new component, add the component to the failover table
   in `docs/RELIABILITY.md` § 7.
