# Oarumi Language Specification

> **Status:** v0.3 (normative sections marked ⚑). Target v1.0 at end of Phase 4.
> **Audience:** linguists, engine implementers, model trainers.

---

## 1. Design principles

1. **Universal semantic core** — 65 NSM primes; anything sayable in any
   language is expressible.
2. **Analytic, agglutinative morphology** — one meaning per morpheme, no
   fusional portmanteaus, no polysynthetic incorporation in the core.
3. **Parallel affective channel** — emotion rides on prosody and particles,
   never consuming propositional bits.
4. **Tri-modal** — spoken, signed, and tactile are first-class renderers of
   the same semantic structure.
5. **Bounded optional modules** — typological accommodations are optional,
   finite, and clearly delimited. The default grammar is stable.

## 2. ⚑ Phonology

### 2.1 Segmental inventory (spoken)

**Vowels (5):** `/a, e, i, o, u/`. No length contrast, no nasal vowels.

**Pulmonic consonants (18):**

| | Bilabial | Alveolar | Velar |
|---|---|---|---|
| Plosive | p b | t d | k g |
| Nasal | m | n | |
| Fricative | f v | s z | |
| Liquid | | l r | |
| Approximant | w | | j |

**Clicks (15):** five click types × three accompaniments.

| Click type | Symbol | Plain | Nasal | Aspirated |
|---|---|---|---|---|
| Bilabial | ʘ | ʘ | ʘ̃ | ʘʰ |
| Dental | ǀ | ǀ | ǀ̃ | ǀʰ |
| Alveolar | ǃ | ǃ | ǃ̃ | ǃʰ |
| Lateral | ǁ | ǁ | ǁ̃ | ǁʰ |
| Palatal | ǂ | ǂ | ǂ̃ | ǂʰ |

**Constraint:** clicks are **word-initial only**. This follows the strong
cross-linguistic tendency and keeps the inventory learnable.

### 2.2 Syllable structure

- Canonical: `CV`, `CVV`, `CVC` (final C restricted to `/n, s, l, r/`).
- Click syllables are always `CV` or `CVV`.
- No onset clusters in the core; loanword adaptation may insert an
  epenthetic vowel.

### 2.3 Tone

Lexical tone is **not used**. Pitch is reserved for the affective and
discourse channel (§ 5). Speakers of tonal languages may use pitch
pragmatically without creating lexical contrast.

### 2.4 Stress

Penultimate by default. Stress is not contrastive.

## 3. ⚑ Morphology

Oarumi is **agglutinative with bounded inventory**. Every affix carries one
meaning. There are no portmanteau morphemes.

### 3.1 Noun phrase

