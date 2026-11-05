# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Spelling checker on desktop and Android. It suggests corrections from a
  per-language frequency dictionary, using edit distance.
- Language detection on the Translate screen. Choose "Detect language" as the
  source; when the answer is unsure, the chosen language is kept.
- Language packs: 6 base packs ship in the app, and 12 extra packs download on
  request. Every download is checked against `language/packs/index.json`.
  Build with `tools/build_language_packs.py`.
- Desktop Packs tab, and an Android Settings screen, to install and remove packs.
- App update check against the latest GitHub release, on desktop and Android.
  Android can download updates in the background (off by default) and asks the
  user to confirm the install.
- Android: save the APK to a chosen location, or share it, from Settings.

### Notes
- Pack licences and data provenance are under review; see
  `language/packs/NOTICE.md`.
- Optional network use is recorded in ADR-0008 and `docs/OFFLINE.md` § 6.

## [0.1.0-alpha.4] - 2026-11-04

### Added
- Dual license: MIT OR Apache-2.0 (`LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE`).
- Local CI/CD runner `tools/ci.py` with preflight checks, a dependency DAG,
  a fingerprint cache and reports; git hooks in `scripts/hooks/`.
- Parity web GUI (`tools/parity_web`) with unit and e2e tests.
- ADR-0006 (parity web GUI) and ADR-0007 (Kotlin parity policy).
- `release-wheel` workflow: builds the sdist and desktop wheel on each `v*` tag.
- Drift test that checks `docs/PARITY_API.md` against the Python engine.
- Post-build name re-check in `docs/NAME.md` (§ 4.1).

### Changed
- Python package version is `0.1.0a4`.
- The unit, parity and nightly android jobs run on Ubuntu.

### Fixed
- `ci_setup.sh` regenerates audio WAVs in fresh clones and no longer hides
  golden-freeze errors.
- `android/gradlew` is executable in the git index.
- `tests/` is a package, so `tests.parity` imports resolve in CI.
- Qt runtime libraries are installed for the unit job.
- The local gate skips the Android step with a reason when no JDK is present.

## [Unreleased]

### Added
- Secure environment settings: a Settings tab in the app (Ctrl+5) and a
  `python -m desktop.settings` CLI. Every setting has a typed control, shows the
  value in use and where it came from, and says when a change applies. Edits are
  saved together, after validation. Secrets go to the OS keychain and are masked
  in the UI and logs; other values go to a JSON file outside the repo. See
  `docs/SETTINGS.md`.
- Desktop shell: File, View, Settings and Help menus; Ctrl+1 to Ctrl+5 switch
  tabs; closing or restarting asks what to do with unsaved settings; a restart
  button applies settings that need one.
- `docs/NAME.md` — name clearance record and re-verification procedure.
- ADR-0005 — the name "Oarumi" and the no-rebrand rule.

### Changed
- (none yet)

### Fixed
- (none yet)

## [0.1.0-alpha.3] - YYYY-MM-DD — "Oarumi" rename

### Changed
- **Project renamed from the working placeholder to `Oarumi`.**
  - Repository: `<org>/omnilingua` → `<org>/oarumi`
  - Python distribution: `omnilingua` → `oarumi`
  - Database file: `language/omnilingua.db` → `language/oarumi.db`
  - Environment variables: `OMNILINGUA_*` → `OARUMI_*`
  - Hugging Face org: `omnilingua` → `oarumi`
  - CLI target value `--to omnilingua` → `--to oarumi`
  - Android applicationId: `com.omnilingua.app` → `com.oarumi.app`
  - All documentation updated in the same commit.
- No functional changes; this release is purely a rename and documentation sweep.

### Added
- `docs/NAME.md`, `docs/TESTING.md`, `docs/AI_MODELS.md`, `docs/LANGUAGE_SPEC.md`.
- ADR-0005.

## [0.1.0-alpha.2] - YYYY-MM-DD

### Added
- Reliability layer: IntentRouter, SymbolicShield, Watchdog, RecoveryFSM.
- Offline strategy documentation and offline test harness.

## [0.1.0-alpha.1] - YYYY-MM-DD

### Added
- Language spec v0.1 (primes, phonology, morphology stubs).
- Python engine stubs.
- Bootstrap script.
- Initial documentation tree.
