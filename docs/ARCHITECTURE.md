# Architecture

> **Audience:** developers and agents making structural changes.
> For orientation, see [README.md](../README.md).

---

## 1. Design axioms

1. **The specification is code.** `language/` is the source of truth; apps
   read it, they do not embed copies.
2. **Translation routes through meaning.** Every translation is
   source → pivot → NSM → target. No direct pair models (ADR-0001).
3. **Every neural component has a deterministic twin.** A neural component
   cannot ship without a parity-tested fallback (ADR-0004).
4. **Offline after bootstrap.** No runtime cloud dependency (ADR-0003).
5. **Modalities are parallel, not derived.** Spoken, signed, and tactile are
   first-class renderers of the same NSM structure (ADR-0002).

## 2. Layer diagram

