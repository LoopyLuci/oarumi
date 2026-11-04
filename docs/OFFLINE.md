# Offline Strategy

> **Guarantee:** Both apps run fully offline after a one-time bootstrap.
> No runtime cloud dependency. See ADR-0003.

---

## 1. Bootstrap

First launch downloads:
- Selected source-language ML Kit models (Android) or Argos packs (desktop), ~30 MB each.
- Offline TTS voice data if not already on device.

Everything else — the language DB, Oarumi audio assets, signing avatar
WebView, model manifests and weights for the Oarumi pipeline — is
**bundled in the installer/APK**.

The bootstrap is a **setup step**, not a runtime dependency. After it, the app
shows "Offline Ready" and operates in airplane mode.

## 2. Per-platform replacements

| Function | Cloud (rejected) | Offline replacement |
|---|---|---|
| Pivot translation | Cloud Translation API | ML Kit (Android) / Argos (Python) |
| NSM decomposition | Cloud LLM | Local Tier A/B/C models |
| TTS | Cloud TTS | Android TTS / eSpeak NG / Piper |
| Signing avatar | JASigning server | CWASA client-side Animgen in WebView |
| Clicks/hum audio | Streamed | Bundled assets |

## 3. Verification

`tests/offline/` runs the full pipeline with the network interface stubbed to
raise on any call. The suite must pass with zero network access.

## 4. Degraded mode

If a bootstrap asset is missing (e.g., user declined a language model):

- IntentRouter detects the missing capability.
- The app shows an explicit **degraded-mode notice** naming what is unavailable.
- The deterministic fallback for that language is used.
- The user is offered a retry of the bootstrap for that asset.

No silent degradation. See `docs/RELIABILITY.md` § 6.

## 5. Bootstrap asset inventory

| Asset | Size | Bundled or downloaded |
|---|---|---|
| `language/oarumi.db` | ~5 MB | Bundled |
| Click/hum audio library | ~8 MB | Bundled |
| Signing avatar WebView bundle | ~40 MB | Bundled |
| Oarumi core model weights | ~120 MB | Bundled |
| ML Kit language models | ~30 MB each | Downloaded (user selects) |
| Argos language packs | ~30 MB each | Downloaded (user selects) |
| TTS voice data | ~20 MB per voice | Downloaded if absent |
