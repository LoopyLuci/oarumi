# ADR-0002: Tri-Modal Architecture

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

The language must serve hearing, Deaf, hard-of-hearing, and DeafBlind users.
Treating sign or tactile as "translation of speech" degrades both.

## Decision

Spoken, signed, and tactile are **first-class renderers of the same NSM
structure**. No modality is derived from another. Each has its own
grammatical resources (clicks for spoken segmental contrast; classifiers for
signed spatial grammar; four-hand reciprocity for tactile).

## Consequences

- The NSM layer must be rich enough to support all three modalities.
- Three renderers must be maintained, each with its own parity suite.
- Modality allocation must be explicit (see LANGUAGE_SPEC § 5–7).
- Redundant co-expression is discouraged; complementary co-expression is
  encouraged.

## Alternatives considered

- **Signed English / manually coded speech** — rejected: imposes spoken
  grammar on a visual modality.
- **Tactile as filtered visual sign** — rejected: Protactile has its own
  grammar and reciprocity.
