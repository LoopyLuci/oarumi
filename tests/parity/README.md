# Parity Test Harness

Three guarantee levels:

1. **Corpus parity (Python)** — `pytest tests/parity` compares every case
   in `data/parity-basic/` against its frozen gold in `data/parity-basic/*.json`.
2. **Cross-platform parity (Python vs Kotlin)** — `./gradlew :engine:test
   --tests oarumi.ParityTest` does the same comparison in Kotlin. ADR-0007
   requires byte equality.
3. **Fault-injection parity** — `pytest tests/fault` proves that each neural
   component fails over deterministically on every trigger in
   `config.yaml#fault_triggers`.

## Running

```bash
# Fast (default corpus, skips missing gold)
pytest tests/parity -q

# Strict (missing gold = failure; matches CI)
OARUMI_STRICT_PARITY=1 pytest tests/parity -q

# Complex corpus (slower; nightly)
pytest tests/parity -q --parity-corpus=parity-complex

# Fault injection
pytest tests/fault -q

# Offline (network calls fail the test)
pytest tests/offline -q

# Cross-platform diff
python tools/parity_compare.py \
  --python /tmp/oarumi-python.json --kotlin /tmp/oarumi-kotlin.json
```

## Refreshing gold

```bash
python tools/generate_parity_corpus.py
python tools/generate_parity_complex.py
python tools/freeze_gold.py --corpus parity-basic
python tools/freeze_gold.py --corpus parity-complex
python tools/freeze_renderer_gold.py
python tools/generate_canary.py
```

Review the diff. Any change to a frozen gold is a **high-risk change**
(AGENT.md § 4) — the language spec, the realizer, or a template changed,
and both engines must be updated in the same PR.

## When the harness fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Python vs gold mismatch | Language spec or template changed | Review the diff; update gold only if the change is intended; update Kotlin in the same PR |
| Kotlin vs gold mismatch | Kotlin engine drift | Port the Python change to Kotlin; ADR-0007 forbids divergence |
| Fault test fails | Shield or FSM regression | Check `tests/parity/data/canary/`; verify `RELIABILITY.md` § 4 triggers |
| Offline test fails | A code path is calling the network | Grep for `urllib`, `requests`, `http`; add the code path to the offline adapter |
