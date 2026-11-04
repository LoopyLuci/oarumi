# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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
