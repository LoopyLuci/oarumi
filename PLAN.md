# PLAN — Roadmap and Milestones

> **Horizon:** 18 months. Re-baselined quarterly. Each milestone has an exit
> criterion that is **testable**, not aspirational.

---

## Phase 0 — Foundation (weeks 1–6) · **status: in progress**

**Goal:** Freeze the language spec v1.0 and the engine interfaces, so
downstream work has a stable target.

| Deliverable | Exit criterion |
|---|---|
| `language/primes.yaml` (65 primes + combinators) | Passes `tools/validate_primes.py`; reviewed by a linguist |
| `language/phonology.yaml` (incl. 15 click phonemes) | Round-trips through `engine/python/phonology.py` |
| `language/schema.sql` + seed data | `sqlite3 language/oarumi.db < schema.sql` succeeds |
| Engine interface stubs (Python + Kotlin) | Both compile; contract tests pass |
| ADR-0001 … ADR-0005 | Merged with two maintainer sign-offs |
| `docs/NAME.md` clearance record | Complete, dated, with re-check schedule |

## Phase 1 — Deterministic Engine (weeks 7–14)

**Goal:** A fully working translation pipeline using **only deterministic
components**. No neural models yet. This establishes the parity baseline.

| Deliverable | Exit criterion |
|---|---|
| Rule-based NSM decomposer (Tier A) | ≥80% exact-prime coverage on the seed corpus |
| Deterministic NSM realizer | Round-trips the seed corpus with ≥95% semantic equivalence |
| Phrasebook pivot translator (5 languages) | 500 high-frequency constructions translate correctly |
| Deterministic TTS (eSpeak NG) + click/hum assets | Audio output is phoneme-valid for the full test set |
| Procedural signing (Animgen/CWASA) | 100 HamNoSys-annotated signs render correctly |
| Tactile realizer (rule-based) | 50 reciprocal constructions produce valid protocol output |
| Full offline desktop app (deterministic only) | Runs in airplane mode; all UI flows work |

**Why this phase matters:** It produces the **fallback paths** that later
neural components must be proven equivalent to. Without this, failover is
untestable.

## Phase 2 — Neural Components with Parity (weeks 15–24)

**Goal:** Add each neural component behind the symbolic shield, with a
passing parity suite against its Phase 1 counterpart.

| Deliverable | Exit criterion |
|---|---|
| NSM decomposer Tier B (distilled student) | Parity suite: ≥60% coverage, 100% validity |
| NSM decomposer Tier C (fine-tuned 8B) | Outperforms Tier B on 200-sample adequacy eval |
| Pivot translator (MobileNMT-style) + LoRA adapters (10 languages) | BLEU ≥ 20 on held-out; INT8 fits memory budget |
| Neural TTS (NeuTTS-2E-style) | MOS ≥ 3.5; click accuracy ≥ 99%; hum contour accuracy ≥ 90% |
| Neural sign diffusion model | Visual realism rating ≥ 3/5 on 50 test signs; falls back for unseen |
| ASR (Whisper base int8) | WER ≤ 15% on Oarumi audio test set |
| Symbolic shield + watchdog + recovery FSM | Fault-injection suite: 100% failover trigger rate |

## Phase 3 — Mobile Parity (weeks 25–32)

**Goal:** Ship the Android app with the same capabilities and guarantees as
desktop, offline.

| Deliverable | Exit criterion |
|---|---|
| Kotlin port of engine + reliability layer | Cross-platform parity test: same inputs → same outputs |
| ML Kit + Argos-equivalent offline translation | All Phase 1 phrasebook + Phase 2 neural paths work on device |
| Android TTS + click/hum assets | Same phoneme-validity test passes on-device |
| WebView CWASA avatar | All signs render at ≥15 fps on mid-tier device |
| Bootstrap wizard (download only chosen languages) | First-run completes offline-ready in ≤5 min on Wi-Fi |
| Haptics for tactile output | Protocol-display parity on supported devices |

## Phase 4 — Expansion and Community (weeks 33–52)

**Goal:** Broaden language coverage, complete documentation, open for
community contribution, and publish the language spec v1.0.

| Deliverable | Exit criterion |
|---|---|
| 30-language pivot coverage | Parallel corpora available for all; adapters trained |
| Synthetic data pipeline for low-resource | Augmentation improves BLEU on 3 held-out low-resource languages |
| Public spec v1.0 + learnable curriculum | Pilot cohort of 20 learners completes a 10-lesson course |
| Full documentation tree | `docs/` passes link check; every ADR has a status |
| Contribution pipeline (human + agent) | 5 external contributions merged using the documented workflow |
| Name re-verification | `docs/NAME.md` re-checked and dated |

---

## Non-goals (explicitly out of scope)

- Becoming a full replacement for natural languages. This is an auxiliary
  interlingua, not a universal second language.
- Runtime cloud inference. All neural paths are on-device after bootstrap.
- Fusional or polysynthetic core grammar. The analytic/agglutinative core is
  a load-bearing decision (ADR-0001).
- Tactile neural production model until an annotated corpus exists (see
  `TACTILE-RESEARCH` in TODO.md).
- Renaming. See ADR-0005.

---

## Dependencies between phases

