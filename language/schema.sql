-- Oarumi language database schema.
-- Canonical DDL for the current schema. 0001_init.sql is the frozen baseline;
-- every later change is a migration in language/migrations/ that makes the
-- migrated database match this file (tools/tests/test_migrate_seed.py checks it).
-- Status vocabulary for every form and decomposition: placeholder | provisional | signed_off.
-- See docs/DICTIONARY.md.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    id          TEXT PRIMARY KEY NOT NULL,     -- e.g. '0001_init'
    applied_at  TEXT NOT NULL,        -- ISO-8601 UTC
    checksum    TEXT NOT NULL         -- sha256 of the migration file
);

CREATE TABLE IF NOT EXISTS primes (
    id            TEXT PRIMARY KEY NOT NULL,   -- uppercase, e.g. 'SOMEONE'
    gloss         TEXT NOT NULL,      -- English gloss
    category      TEXT NOT NULL,      -- substantives | determiners | ...
    combinators   TEXT NOT NULL,      -- JSON array of allowed combinator types
    spoken_form   TEXT NOT NULL,      -- IPA-ish surface for the prime
    signed_form   TEXT NOT NULL,      -- HamNoSys ID reference
    tactile_form  TEXT NOT NULL,      -- protocol primitive ID
    nsm_version   TEXT NOT NULL,      -- e.g. 'goddard-wierzbicka-2014'
    form_status   TEXT NOT NULL DEFAULT 'placeholder'
                  CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'))
);

CREATE TABLE IF NOT EXISTS lexemes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    phon_form   TEXT NOT NULL UNIQUE,
    click       TEXT,                  -- NULL or one of the 5 click types
    tone        TEXT,                  -- reserved; lexical tone is not used
    gloss       TEXT NOT NULL,         -- headword gloss
    root_class  TEXT NOT NULL,         -- noun | verb | modifier | particle (checked by the seed)
    frequency   INTEGER NOT NULL DEFAULT 0,  -- Zipfian ordering input
    form_status TEXT NOT NULL DEFAULT 'provisional'
                CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'))
);
CREATE INDEX IF NOT EXISTS idx_lexemes_root_class ON lexemes(root_class, frequency);

CREATE TABLE IF NOT EXISTS senses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    lexeme_id     INTEGER NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
    sense_no      INTEGER NOT NULL DEFAULT 1,      -- 1-based order within the lexeme
    prime_decomp  TEXT NOT NULL,       -- JSON NSMStructure fragment
    decomp_status TEXT NOT NULL DEFAULT 'placeholder'
                  CHECK (decomp_status IN ('placeholder', 'provisional', 'signed_off')),
    gloss         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_senses_lexeme ON senses(lexeme_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_senses_lexeme_no ON senses(lexeme_id, sense_no);

CREATE TABLE IF NOT EXISTS signs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    lexeme_id   INTEGER NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
    hamnosys    TEXT NOT NULL,          -- HamNoSys annotation string; '' until a linguist supplies it
    nonmanual   TEXT NOT NULL DEFAULT '{}',  -- JSON of face/head/mouth morphemes
    form_status TEXT NOT NULL DEFAULT 'placeholder'
                CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'))
);
CREATE INDEX IF NOT EXISTS idx_signs_lexeme ON signs(lexeme_id);

CREATE TABLE IF NOT EXISTS tactile (
    id            INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    sign_id       INTEGER NOT NULL REFERENCES signs(id) ON DELETE CASCADE,
    protocol_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tactile_sign ON tactile(sign_id);

CREATE TABLE IF NOT EXISTS parity_gold (
    id          INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    component   TEXT NOT NULL,          -- pivot | nsm_decompose | nsm_realize | tts | sign | tactile
    input_hash  TEXT NOT NULL,          -- sha256 of the canonical request JSON
    output_json TEXT NOT NULL,
    frozen_at   TEXT NOT NULL,
    UNIQUE(component, input_hash)
);
CREATE INDEX IF NOT EXISTS idx_gold_component ON parity_gold(component);
