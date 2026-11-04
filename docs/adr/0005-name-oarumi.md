# ADR-0005: The Project Name Is "Oarumi"

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** @maintainer, @backup

## Context

Earlier candidate names were either **borrowed roots** (Latin/Greek
derivatives such as *Veritas*, *Alethia*, *Lingua Vera*) or **simple CV
coinages that collided with live trademarks** (*Seluna*, which has live USPTO
and UKIPO filings in software and pharma). The project needs a name that is
original by construction and clear in the relevant classes.

## Decision

The project is named **Oarumi**.

- It is an **original coinage**, not derived from any natural-language root.
- It was produced by a **phonotactic-originality** method: a diphthong-heavy
  CVV shape built only from globally widespread phonemes.
- It is **not translated**; non-Latin scripts use phonetic transliteration.
- Renaming is a high-risk change and requires an ADR superseding this one.

## Consequences

- All repository identifiers, package names, domains, and documentation use
  `Oarumi` / `oarumi`.
- The rename from the working placeholder is recorded in CHANGELOG
  v0.1.0-alpha.3.
- Clearance must be re-verified annually and before any major launch
  (`docs/NAME.md` § 4).
- Agents must never invent alternative names or "improve" the name into a
  Latin/Greek derivative.

## Alternatives considered

- **Classical-root names** (*Veritas*, *Alethia*) — rejected: borrowed, not
  original.
- **Simple CV coinages** (*Seluna*, *Kalivo*) — rejected: high collision risk
  with existing trademarks and products.
- **Kaleth** — considered; usable but carries a regional Basque project and
  notable cultural/search noise. Oarumi was cleaner.
