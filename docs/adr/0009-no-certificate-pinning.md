# ADR-0009: No Certificate Pinning for GitHub Downloads

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** maintainer

## Context

The Android app downloads release metadata, the APK, and language packs from
GitHub hosts. The network security config pinned the certificate chains of
those hosts, so a rogue certificate authority could not impersonate them.

Pinning protects confidentiality and availability only. It does not protect
integrity, because the content is already checked elsewhere:

- Each language pack is checked against `index.json`, which is bundled in the
  signed APK (see ADR-0008 and `stageLanguagePacks` in
  `android/app/build.gradle.kts`). A substituted pack fails the SHA-256 check.
- The APK is checked by the system installer, which refuses an update not
  signed with the installed app's key.

The pins also carried real costs. They expired on 2027-11-05, and Android stops
enforcing them silently at that point. A CA change blocks downloads until a new
build ships. Corporate TLS inspection breaks updates for those users.

## Decision

Remove the `pin-set` from `network_security_config.xml`. Keep TLS with the
system trust store, and keep cleartext traffic refused for the GitHub domains.

## Consequences

- A network attacker with a rogue certificate can read download traffic (which
  packs, which version) or block downloads. It cannot alter the installed
  content.
- CodeQL rule `java/android/missing-certificate-pinning` reports again.
- If packs or the pack index ever come from the network at runtime, this
  decision needs revisiting. Sign the index then, with an ECDSA P-256 key whose
  public half ships in the APK. Ed25519 needs API 33, and `minSdk` is 26.
