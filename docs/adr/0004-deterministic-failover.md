# ADR-0004: Deterministic Failover for Every Neural Component

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

Neural components can fail silently, produce invalid output, or become
unavailable offline. Without a deterministic fallback, there is no reliability
guarantee.

## Decision

Every neural component must have a deterministic counterpart with a defined
parity contract and automatic failover on auditable triggers. A component
without a passing parity suite cannot ship. Failover triggers are evaluated
by deterministic code, never by the neural model. Recovery is canary-gated.

## Consequences

- Phase 1 (deterministic engine) must complete before Phase 2 (neural
  components), because Phase 2's exit criteria are parity against Phase 1.
- Every component has two implementations and two test suites.
- Model updates require re-running parity suites before release.
- The system degrades gracefully and audibly; it never fails silently.

## Alternatives considered

- **Fail-open with error messages** — rejected: the app must remain useful
  offline, not just report failure.
- **Single neural path with no fallback** — rejected: violates the offline
  guarantee and the reliability invariant.
- **Cloud fallback** — rejected: violates ADR-0003.
