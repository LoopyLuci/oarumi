# AGENT.md — Instructions for AI Agents Operating on This Repository

> **Audience:** Any AI agent (LLM-based coding assistant, autonomous agent,
> CI bot) that reads, modifies, or reviews this repository.
>
> **Rule zero:** If you are an agent and you are about to make a change that
> affects the language spec (`language/`), the parity contracts
> (`tests/parity/`), the failover logic (`engine/*/reliability/`), or the
> project name, stop and follow § 4 (High-Risk Changes) before proceeding.

---

## 1. What kind of project this is

This is a **language + engine + two applications** project. It is unusual in
that the "product" is partly a specification (the Oarumi language) and partly
software. Agents must understand that **the specification is code**: a change
to `language/primes.yaml` changes every downstream renderer, every test, and
every model's training target. Treat language files as APIs.

## 2. Ground truth priority

When documents conflict, trust in this order:

1. **Schema and data files** (`language/schema.sql`, `language/*.yaml`) — the machine-readable truth.
2. **Tests** (`tests/`) — executable truth.
3. **ADRs** (`docs/adr/`) — the *why* behind design decisions.
4. **ARCHITECTURE.md / LANGUAGE_SPEC.md** — human-readable truth; may lag.
5. **README / HANDOVER / PLAN / TODO** — orientation, may lag.

If you find a conflict, **do not silently resolve it**. Open an issue tagged
`doc-drift` and, if you can, fix the lower-priority document.

## 3. Standard agent workflow

Every agent change follows this loop:

1. **Orient**: read `HANDOVER.md` § 5 (load-bearing decisions) and `TODO.md`.
2. **Claim**: find or create an issue. Add the label `agent-working` and a
   comment with your identity and intended scope. Do not work on unclaimed
   tasks.
3. **Branch**: `agent/<short-id>/<slug>` (e.g., `agent/claude-4/nsm-validator-tests`).
4. **Change small**: one logical change per PR. Do not bundle fixes.
5. **Test locally**: `./scripts/verify_all.sh` must pass. For model changes,
   run parity suites with `OARUMI_STRICT_PARITY=1`.
6. **Document**: update the relevant doc *in the same PR*. If you changed a
   language file, update `LANGUAGE_SPEC.md` and add a changelog entry.
7. **PR**: use the template. Tag `agent-authored`. Describe *what*, *why*, and
   *how you verified*.
8. **Wait for human review** for anything in § 4. Agents cannot self-merge
   high-risk changes.

## 4. High-risk changes (require human sign-off)

| Area | Examples | Why |
|---|---|---|
| **Language spec** | Adding/removing NSM primes, changing morphosyntax, changing click inventory | Cascades to every component and every model |
| **Parity contracts** | Changing fallback behavior, thresholds, or coverage guarantees | Defines reliability guarantees users depend on |
| **Failover logic** | New triggers, changed recovery FSM, watchdog timing | Safety-critical; must be audited |
| **Model manifests** | Publishing new model versions, changing hashes | Supply-chain integrity |
| **Project name / branding** | Any change to "Oarumi", its spelling, or its transliterations | Legal + community identity |
| **Secrets / CI** | Any change to `.github/workflows/` or secret usage | Security-sensitive |
| **License** | Any change | Legal |

Everything else (tests, docs, refactors, UI, tooling) is normal-risk and may
be merged after standard review.

## 5. Things agents must never do

- **Never** commit model binaries directly. Use the manifest + download script.
- **Never** hardcode credentials. Request secrets via an issue and let a human provision them.
- **Never** disable a test to make CI pass. Fix it or mark `@pytest.mark.xfail(reason=..., link=...)`.
- **Never** change a parity threshold without also changing the test data and updating `RELIABILITY.md`.
- **Never** edit `language/schema.sql` without a matching migration in `language/migrations/`.
- **Never** touch `HANDOVER.md` § 5 without an ADR.
- **Never** invent a new name or a rebrand. The name is fixed by ADR-0005.
- **Never** assume previous conversation state. If context is missing, re-read this file and `HANDOVER.md`.

## 6. How to run the project

```bash
./scripts/bootstrap.sh              # first time only
./scripts/verify_all.sh             # all validators + tests
./tools/cli --help                  # CLI surface
python -m desktop.app               # desktop
cd android && ./gradlew :app:test   # android unit tests
```

## 7. Where to look for context

| Question | File |
|---|---|
| What is this project? | `README.md` |
| Why is it called Oarumi? | `docs/NAME.md` |
| What's the current state? | `HANDOVER.md` § 1 |
| What's the plan? | `PLAN.md` |
| What's next? | `TODO.md` |
| How does the language work? | `docs/LANGUAGE_SPEC.md` |
| How does the system work? | `docs/ARCHITECTURE.md` |
| How do models work? | `docs/AI_MODELS.md` |
| How does failover work? | `docs/RELIABILITY.md` |
| How is data shaped? | `docs/DATA_FORMATS.md` |
| How do I test? | `docs/TESTING.md` |
| Why was decision X made? | `docs/adr/` |

## 8. Reporting

Agents should post a summary in the issue at three points: after claiming,
after opening the PR, and after merge (or abandonment). The summary must
include: what changed, what you verified, what you did **not** verify, and any
follow-up issues you created. This is the audit trail.

## 9. If you are unsure

Open an issue tagged `agent-question`. Do not proceed on ambiguous high-risk
changes. A blocked agent is far cheaper than a broken language spec.
