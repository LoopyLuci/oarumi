# HANDOVER — Project Continuity Document

> **Purpose:** This file must contain everything a new maintainer (human or
> agent) needs to take over the project without prior context. Update it at
> every release and whenever ownership, infrastructure, or critical dependencies
> change. If you are inheriting this project and the information here is stale,
> trust the repository state (git log, issues, CI) over this document, and then
> update this document.

---

## 1. Project state (last updated: YYYY-MM-DD, by <name>)

| Dimension | State |
|---|---|
| **Name** | Oarumi (original coinage; see docs/NAME.md) |
| **Lifecycle** | Pre-alpha → Alpha → Beta → Stable |
| **Current phase** | Pre-alpha: language spec v0.3 stable; engine interfaces frozen; app UIs in development |
| **Latest release** | v0.1.0-alpha.3 (rename release — see CHANGELOG.md) |
| **Next milestone** | M2: offline translation pipeline end-to-end (see PLAN.md) |
| **Known blockers** | (list any active blockers with issue links) |

## 2. Ownership and access

| Area | Primary owner | Backup | Access notes |
|---|---|---|---|
| Repo (GitHub) `oarumi/oarumi` | @maintainer | @backup | Admin on org |
| Model hosting | Hugging Face org `oarumi` | @backup | Write token in `MODEL_HF_TOKEN` secret |
| Release signing (Android) | @maintainer | @backup | Keystore in `ANDROID_KEYSTORE_B64` secret |
| CI infrastructure | GitHub Actions | — | Workflows in `.github/workflows/` |
| Domain `oarumi.com` | @maintainer | @backup | Registrar + DNS creds in org vault |
| PyPI project `oarumi` | @maintainer | @backup | Trusted publishing via GitHub OIDC |
| Community channels | Discord / Matrix | @backup | Invite in pinned issue #1 |

## 3. Critical dependencies and their risk

| Dependency | Role | Risk if unavailable | Mitigation |
|---|---|---|---|
| NSM prime inventory (Goddard & Wierzbicka) | Semantic core | Language loses its universal foundation | Frozen copy in `language/primes.yaml`; cite source in NOTICE |
| ML Kit on-device translation | Android pivot translation | Android app loses offline translation | Argos fallback bundle as secondary APK flavor |
| Argos Translate | Desktop pivot translation | Desktop loses offline translation | Phrasebook fallback + structured degradation notice |
| CWASA / SiGML | Signing avatar | Signed modality unavailable | Pre-rendered animation clips bundled; avatar disabled in degraded mode |
| Whisper ggml | ASR | Spoken input unavailable | Text input always available; app remains functional |

## 4. Where things live

- **Language definition** → `language/` (source of truth; all apps read this)
- **Engine reference implementation** → `engine/python/`
- **Model manifests & training** → `models/`
- **Parity test suites** → `tests/parity/`
- **Architecture decisions** → `docs/adr/`
- **Name clearance record** → `docs/NAME.md`
- **Roadmap** → `PLAN.md`
- **Task backlog** → `TODO.md`

## 5. Decisions that must not be silently reversed

These are load-bearing architectural commitments. To change any, open an ADR
and get sign-off from two maintainers.

1. **Pivot-and-NSM translation pipeline** (ADR-0001). Direct language pairs
   are not added; all translation routes through NSM.
2. **Tri-modal architecture** (ADR-0002). Spoken, signed, and tactile are
   first-class; no modality is "translation of" another.
3. **On-device inference only after bootstrap** (ADR-0003). No runtime cloud
   dependency is allowed.
4. **Deterministic failover for every neural component** (ADR-0004). A neural
   component without a parity-tested fallback cannot ship.
5. **Analytic/agglutinative core.** No fusional or polysynthetic core grammar.
6. **The name is Oarumi** (ADR-0005). It is an original coinage, not a
   borrowed root. Do not "improve" it into a Latin or Greek derivative.

## 6. Runbooks

### 6.1 Release a new version

1. Update `CHANGELOG.md` and bump version in `pyproject.toml` and `android/app/build.gradle.kts`.
2. Run `./scripts/verify_all.sh` — must pass on all platforms.
3. Tag `vX.Y.Z`; CI builds desktop wheels and Android APK.
4. Publish release notes; link to parity test results.
5. Announce in community channels.
6. Update § 1 of this file.

### 6.2 Rotate a secret

1. Update the GitHub secret.
2. If a model token: revoke old token on Hugging Face, regenerate.
3. If Android keystore: **do not rotate silently** — store continuity depends on it; coordinate with store listing.

### 6.3 If CI is broken and you're taking over

1. Run `./scripts/verify_all.sh` locally to reproduce.
2. Check whether failures are in `tests/parity/` (likely model drift) or `tests/unit/` (likely a code change).
3. Parity failures: re-run with `OARUMI_STRICT_PARITY=1` and inspect `tests/parity/reports/`.
4. If a model manifest hash mismatches, open an issue tagged `model-integrity`.

### 6.4 Re-verify the project name

Annually, or before any major public launch:

1. Re-run the checks in `docs/NAME.md` § 4 (trademark, packages, domains, stores, conlang directories).
2. Renew `oarumi.com`, `oarumi.org`, `oarumi.dev`.
3. Record results with a date stamp in `docs/NAME.md`.

## 7. Known debt

- Tactile realizer is rule-based; no trained model exists yet (see TODO.md `TACTILE-*`).
- Low-resource language coverage in the pivot translator is limited to
  languages with available parallel corpora; the synthetic data pipeline is
  specified but not yet trained.
- Desktop signing avatar performance on older GPUs is untested.
- `docs/LANGUAGE_SPEC.md` § 7 (tactile grammar) is normative but thin.

## 8. Handover checklist

Before declaring the handover complete:

- [ ] All secrets are stored in the org, not in personal accounts.
- [ ] At least two people/agents have admin on the repo, model host, domain, and store listings.
- [ ] This document has been read and updated by the inheritor.
- [ ] A test release was performed end-to-end by the inheritor.
- [ ] All open issues have an `owner:` label or are in `TODO.md`.
