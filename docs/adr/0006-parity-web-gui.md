# ADR-0006: Parity Web GUI

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

Parity between the Python engine, the Kotlin engine, and the frozen gold set
must be observable by humans and agents without reading CI logs. A local,
build-step-free interface lowers the cost of verification and makes failover
events visible.

## Decision

Ship a local FastAPI server plus a vanilla-JS single-page frontend at
`tools/parity_web/`, exposing the C6 API. No build step. Runs on
`localhost:8090`.

## Consequences

- Verification is a first-class, inspectable artifact.
- The GUI is part of `verify_all.sh` in smoke form.
- No dependency on a hosted dashboard or external service.
