# Oarumi

A universal interlingua with a deterministic, offline, tri-modal language engine —
designed for accurate data transfer, emotional fidelity, and full accessibility.

> **Status:** Pre-alpha. The language specification and engine interfaces are
> stable; the model stack and applications are in active development. See
> [PLAN.md](PLAN.md) for milestones.

---

## What this is

Oarumi is three things in one repository:

1. **A constructed language** with a universal semantic core (65 NSM primes),
   bounded analytic morphosyntax, and tri-modal expression (spoken, signed,
   tactile).
2. **A translation engine** that converts any supported source language to the
   interlingua and back, using an English pivot and an NSM semantic layer.
3. **Two native applications** — a Python desktop GUI and a Kotlin Android app —
   that run **fully offline** after a one-time bootstrap, and that **never fail
   silently**: every neural component has a deterministic counterpart with a
   parity contract and automatic failover.

---

## Who this is for

| You are... | Start here |
|---|---|
| **A user** who wants to run the app | [§ Quick start](#quick-start) |
| **A linguist** interested in the language | [docs/LANGUAGE_SPEC.md](docs/LANGUAGE_SPEC.md) |
| **A developer** wanting to contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |
| **An AI agent** operating on this repo | [AGENT.md](AGENT.md) |
| **A maintainer** taking over | [HANDOVER.md](HANDOVER.md) |
| **Curious about the architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

---

## Quick start

### Desktop (Python 3.11+)

```bash
git clone https://github.com/LoopyLuci/oarumi.git
cd oarumi
./scripts/bootstrap.sh          # venv, deps, language DB, audio assets, dev stubs
python -m desktop.app           # launches the GUI
```

The bootstrap is idempotent. It installs dependencies, seeds the language
database, generates the audio assets and fetches **development model stubs**.
Real neural model weights are not shipped yet, so neural components currently
fall back to their deterministic counterparts. The engine reports this as
`degraded` with a failover trace rather than hiding it.

### Android

Download the APK from [Releases](../../releases) or build locally:

```bash
cd android
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

On first launch, select your source languages. The app downloads only those
ML Kit models (~30 MB each). After that, everything is on-device.

### CLI (for scripting and testing)

```bash
python -m tools.cli translate --from es --to oarumi --modality spoken "hola"
python -m tools.cli decompose "hello"         # NSM structure for an English pivot
python -m tools.cli validate                  # run schema and prime validators
```

Settings (including secrets, which are kept in your OS keychain) are managed from
**Settings → Environment variables** in the app, or with `python -m desktop.settings`.
See [docs/SETTINGS.md](docs/SETTINGS.md).

Translation currently covers a seed phrasebook for Arabic, German, Spanish,
French and Chinese. Phrases outside it come back `degraded` with the reason.

---

## Architecture at a glance

```
text ──► pivot (phrasebook → English) ──► NSM decomposer ──► NSM realiser
                                                              │
                                          NSM validator ◄─────┘
                                                │
                                  OarumiSurface ├──► spoken   (audio assets, TTS)
                                                ├──► signed   (HamNoSys → SiGML)
                                                └──► tactile  (protocol cells)
```

Every neural step has a deterministic counterpart. The reliability layer
(`oarumi/reliability`) runs each neural component behind a symbolic shield with
a parity contract, a watchdog and a recovery state machine, and records every
failover in an audit log. The full design is in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## License

Oarumi is dual-licensed under either of [Apache License 2.0](LICENSE-APACHE)
or [MIT License](LICENSE-MIT), at your option. See [LICENSE](LICENSE).
