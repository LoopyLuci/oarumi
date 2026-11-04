# ADR-0003: On-Device Inference After Bootstrap

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

The apps must work offline, in remote areas, and on devices without reliable
network access. Runtime cloud inference would violate this.

## Decision

After a one-time bootstrap (downloading selected language models), **all
inference runs on-device**. No runtime cloud dependency is permitted. Cloud
services are never called by the shipping app.

## Consequences

- Models must be compressed to fit device budgets (see AI_MODELS § 5).
- The bootstrap is a setup step, not a runtime dependency.
- A degraded mode is required for missing bootstrap assets (OFFLINE § 4).
- Cloud-based components (e.g., cloud TTS) are excluded from the product.

## Alternatives considered

- **Cloud inference with offline cache** — rejected: violates the offline
  guarantee for uncached input.
- **Hybrid with cloud fallback** — rejected: same problem; also introduces
  silent degradation.
