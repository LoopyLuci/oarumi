# Reliability: Deterministic Failover and Self-Healing

> **Audience:** anyone touching `engine/*/reliability/` or `tests/parity/`.
> This document is the contract those directories implement.

---

## 1. The invariant

**Every neural component has a deterministic counterpart with a defined
parity contract. Failover is automatic, deterministic, and auditable.**

A component that violates this invariant cannot ship.

## 2. Execution tiers

| Tier | What | Determinism |
|---|---|---|
| 1 | IntentRouter — classifies, selects lane | 100% |
| 2 | Neural path — handles ambiguous input | Stochastic |
| 3 | Deterministic fallback | 100% |

## 3. Parity contract (a vector, not a scalar)

| Dimension | Meaning | How measured |
|---|---|---|
| Semantic equivalence | Same meaning for in-domain inputs | Back-translation + adequacy rating |
| Functional coverage | % of neural path's input domain handled | Coverage matrix by language/modality |
| Latency ceiling | P95 on target hardware | Benchmarks in `tests/bench/` |
| Modality coverage | Output in required modality | Modality-specific acceptance tests |
| Safety invariants | Never violates hard constraints | Runtime monitor + formal spec |

Thresholds are per-component and live in `tests/parity/config.yaml`.
Changing a threshold is a high-risk change.

## 4. Failover triggers (deterministic)

- **Validation failure** — output violates schema / prime inventory / grammar
- **Confidence below threshold** — calibrated score below floor
- **Latency breach** — P95 deadline exceeded
- **Resource exhaustion** — memory/compute/battery below margin
- **Integrity failure** — model hash mismatch or memory corruption
- **Repeated inconsistency** — same input, divergent outputs across runs

Triggers are evaluated by deterministic code, never by the neural model.

## 5. Recovery state machine

