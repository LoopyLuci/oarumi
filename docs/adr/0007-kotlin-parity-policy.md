# ADR-0007: Kotlin Engine Is a Bit-Exact Port

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

Two implementations of the same pipeline will drift unless the relationship is
stated. A "close enough" policy lets silent divergence accumulate.

## Decision

The Kotlin engine is a **bit-exact port** of the Python engine for the
deterministic path. Any divergence on the parity corpus is a **bug in Kotlin**,
not an acceptable platform difference. Neural paths may differ within their
parity contracts, but the deterministic fallback must be identical.

## Consequences

- Batch 7's `ParityTest` asserts JSON equality, not similarity.
- Any Python change to the deterministic path requires a matching Kotlin change
  in the same release.
- `tools/parity_compare.py` treats a deterministic-path diff as a hard failure.
