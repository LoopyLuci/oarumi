# ADR-0001: Pivot-and-NSM Translation Pipeline

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

The project must translate between "any" source and target languages. Building
direct models for every pair is O(n²) and infeasible for ~7,000 languages.

## Decision

All translation routes through a **pivot language (English)** and an **NSM
semantic layer**: source → pivot → NSM → target. No direct pair models are
added. Low-resource coverage is handled by LoRA adapters on the pivot
translator and by synthetic parallel data generated through the NSM pipeline.

## Consequences

- The number of models scales linearly with languages, not quadratically.
- Translation quality is bounded by the quality of NSM decomposition, which
  becomes the critical component.
- The NSM decomposer is the only place where meaning is represented, so it
  must be the most rigorously validated component.
- Direct pair models are explicitly out of scope.

## Alternatives considered

- **Direct pair models** — rejected: O(n²), infeasible.
- **Single multilingual model without NSM** — rejected: no semantic
  invariant, no cross-modal anchor, no parity baseline.
