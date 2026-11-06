-- 0002_dictionary_entries: dictionary entry model. See docs/DICTIONARY.md.
-- Brings a 0001 database to the state described in language/schema.sql.
-- Status vocabulary: placeholder | provisional | signed_off.

ALTER TABLE primes ADD COLUMN form_status TEXT NOT NULL DEFAULT 'placeholder'
    CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'));

ALTER TABLE lexemes ADD COLUMN form_status TEXT NOT NULL DEFAULT 'provisional'
    CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'));
CREATE INDEX IF NOT EXISTS idx_lexemes_root_class ON lexemes(root_class, frequency);

ALTER TABLE senses ADD COLUMN sense_no INTEGER NOT NULL DEFAULT 1;
ALTER TABLE senses ADD COLUMN decomp_status TEXT NOT NULL DEFAULT 'placeholder'
    CHECK (decomp_status IN ('placeholder', 'provisional', 'signed_off'));
CREATE UNIQUE INDEX IF NOT EXISTS idx_senses_lexeme_no ON senses(lexeme_id, sense_no);

ALTER TABLE signs ADD COLUMN form_status TEXT NOT NULL DEFAULT 'placeholder'
    CHECK (form_status IN ('placeholder', 'provisional', 'signed_off'));
