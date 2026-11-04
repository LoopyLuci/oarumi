# Data Formats

## SQLite schema

Canonical schema: `language/schema.sql`. Migrations: `language/migrations/`,
applied by `tools/migrate.py`. Database file: **`language/oarumi.db`**.

### Tables

| Table | Purpose | Key columns |
|---|---|---|
| `primes` | NSM primes + combinators | `id`, `name`, `gloss`, `combinator` |
| `lexemes` | Conventionalized roots | `id`, `phon_form`, `click`, `tone` |
| `senses` | Meanings attached to lexemes | `id`, `lexeme_id`, `prime_decomp` |
| `signs` | HamNoSys annotations | `id`, `lexeme_id`, `hamnosys`, `nonmanual` |
| `tactile` | Protactile constructions | `id`, `sign_id`, `protocol_json` |
| `parity_gold` | Frozen expected outputs | `id`, `component`, `input_hash`, `output_json` |
| `schema_migrations` | Applied migration log | `id`, `applied_at`, `checksum` |

### Migrations

1. Numbered: `0001_init.sql`, `0002_add_signs.sql`.
2. Forward-only; idempotent where possible.
3. `tools/migrate.py` applies pending migrations in order and records them.

## YAML files

All YAML under `language/` is validated by `tools/validate_schemas.py`
against JSON Schema files in `language/schemas/`. A validation failure blocks CI.

## JSON output schemas

| Format | Shape |
|---|---|
| `NSMStructure` | `{ "primes": [...], "combinators": [...] }` |
| `OarumiSurface` | `{ "phonemes": [...], "clitics": [...], "mood": "..." }` |
| `SigML` | XML per SiGML spec |
| `TactileProtocol` | `{ "conveyer_hand": "...", "receiver_location": "...", "movement": "...", "contact": "...", "referent_id": "..." }` |

Schemas live in `engine/schemas/` and are versioned.

## Model manifests

See `docs/AI_MODELS.md` § 6. Manifests are JSON, signed, and hash-pinned.

## Change discipline

Any schema change requires:
1. A migration (SQLite).
2. A JSON Schema update.
3. A parity gold update if it changes outputs.
4. A CHANGELOG entry.
5. Two-maintainer sign-off.
