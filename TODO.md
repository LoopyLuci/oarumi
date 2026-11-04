# TODO — Task Backlog

> Conventions:
> - Every item has a stable ID. Reference it in branches and PRs.
> - `P0` = blocks a milestone; `P1` = should ship with milestone; `P2` = nice to have.
> - Owner accepts `@human`, `agent`, or blank (unclaimed).
> - Completed items move to CHANGELOG.md and are removed here at each release.

---

## Phase 0 — Foundation

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| FOUND-001 | P0 | Finalize `primes.yaml` with combinators | @linguist | Review against Goddard 2021 |
| FOUND-002 | P0 | Phonology: 5 click types, 3 accompaniments, CV syllables | agent | See LANGUAGE_SPEC § 3 |
| FOUND-003 | P0 | Schema migration runner | agent | `tools/migrate.py` |
| FOUND-004 | P0 | Contract test harness for engine interfaces | agent | Both Python + Kotlin |
| FOUND-005 | P1 | ADR-0004 wording reviewed for parity thresholds | @maintainer | |
| FOUND-006 | P1 | Glossary of typology terms | agent | `docs/GLOSSARY.md` |
| FOUND-007 | P0 | `docs/NAME.md` with dated clearance record | @maintainer | Rename completed; record pending |

## Phase 1 — Deterministic Engine

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| DET-001 | P0 | Rule-based NSM decomposer (Tier A) | agent | Template library |
| DET-002 | P0 | Deterministic NSM realizer | agent | Transducer |
| DET-003 | P0 | Phrasebook translator (en, es, zh, ar, hi) | agent | |
| DET-004 | P0 | eSpeak NG adapter with SSML + click assets | agent | |
| DET-005 | P0 | Procedural Animgen avatar (desktop) | agent | WebView integration |
| DET-006 | P0 | Tactile protocol encoder | agent | 50 construction corpus |
| DET-007 | P1 | Deterministic parity baseline report | @maintainer | Freeze as gold outputs |
| DET-008 | P1 | Full offline desktop MVP | agent | Airplane mode test |

## Phase 2 — Neural Components

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| NEUR-001 | P0 | Symbolic shield + watchdog + recovery FSM | agent | See RELIABILITY.md |
| NEUR-002 | P0 | Fault-injection test suite | agent | Required for NEUR-001 exit |
| NEUR-003 | P0 | Distilled NSM decomposer (Tier B) | agent | Parity suite |
| NEUR-004 | P0 | MobileNMT-style pivot translator + LoRA | agent | |
| NEUR-005 | P1 | Fine-tuned Tier C NSM decomposer | agent | |
| NEUR-006 | P1 | Neural TTS with click-masked loss | agent | NeuTTS-2E template |
| NEUR-007 | P1 | Neural sign diffusion model | agent | |
| NEUR-008 | P1 | Whisper ASR adapter | agent | |
| NEUR-009 | P2 | Auto-revert on regression | agent | |

## Phase 3 — Mobile Parity

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| MOB-001 | P0 | Kotlin port of engine + reliability | agent | KMP where possible |
| MOB-002 | P0 | ML Kit translation integration | agent | |
| MOB-003 | P0 | Android TTS + click assets | agent | |
| MOB-004 | P0 | WebView CWASA avatar | agent | |
| MOB-005 | P0 | Bootstrap wizard (per-language downloads) | agent | |
| MOB-006 | P1 | Cross-platform parity test harness | @maintainer | Same I/O → same output |
| MOB-007 | P1 | Haptic protocol rendering | agent | |
| MOB-008 | P2 | Low-end device performance profile | agent | |

## Phase 4 — Expansion

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| EXP-001 | P0 | 30-language pivot coverage | @maintainer | |
| EXP-002 | P1 | Synthetic data pipeline for low-resource | agent | |
| EXP-003 | P1 | Public spec v1.0 + 10-lesson curriculum | @linguist | |
| EXP-004 | P1 | Documentation link checker | agent | |
| EXP-005 | P2 | Community onboarding walkthrough video | @maintainer | |

## Cross-cutting

| ID | Pri | Task | Owner | Notes |
|---|---|---|---|---|
| NAME-001 | P1 | Annual name re-verification (trademark, domains, packages, stores) | @maintainer | Process in `docs/NAME.md` § 4 |
| TACTILE-RESEARCH | P1 | Protactile corpus collection plan | @linguist | Prerequisite for tactile neural model |
| DOC-001 | P0 | Keep HANDOVER.md current at every release | @maintainer | Checklist in HANDOVER § 6.1 |
| DOC-002 | P1 | Every ADR has a status field | agent | accepted / superseded / proposed |
| SEC-001 | P1 | Threat model for model supply chain | @maintainer | |
| TEST-001 | P0 | `verify_all.sh` runs on CI for all platforms | agent | |
| TEST-002 | P1 | Parity suites run with `OARUMI_STRICT_PARITY=1` on CI | agent | |
