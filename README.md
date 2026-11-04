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
git clone https://github.com/<org>/oarumi.git
cd oarumi
./scripts/bootstrap.sh          # installs deps, downloads models, seeds DB
python -m desktop.app           # launches the GUI
```

The bootstrap downloads ~200 MB of language packs and model weights.
After it completes, the app runs fully offline.

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
./tools/cli translate --from es --to oarumi --modality spoken "Hola, mundo"
./tools/cli decompose "Hello, world"          # NSM structure
./tools/cli validate --all                    # run all schema validators
```

---

## Architecture at a glance

