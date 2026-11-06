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
| Language packs, base (6 languages) | 27–631 KB each | Bundled |
| Language packs, extra (12 languages) | 23–635 KB each | Downloaded (user selects) |

## 6. Optional network use

Three actions reach the network. Each runs only when the user starts it. The
translation and detection pipeline never does.

| Action | Request | Kept |
|---|---|---|
| Download an extra language pack | `raw.githubusercontent.com` pack file | Yes, after its size and SHA-256 match `language/packs/index.json` |
| Check for an app update | `api.github.com` latest release | No |
| Download an Android APK update | GitHub release APK asset | Yes, after its SHA-256 digest matches; kept until installed |

Background update checks are off by default. Turning on "Download updates in
the background" on Android checks at most every 12 hours, on a connected
network. It downloads only when a newer release has a digest. Installing always
asks the user to confirm. Requests send only `User-Agent` and `Accept` headers.
See [ADR-0008](adr/0008-optional-network-for-packs-and-updates.md).
