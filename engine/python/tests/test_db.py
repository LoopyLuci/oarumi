"""DB interface tests against the seeded SQLite file. Entry model: docs/DICTIONARY.md."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from oarumi.db import LanguageDb


def test_prime_lookup(db: LanguageDb) -> None:
    p = db.get_prime("WANT")
    assert p is not None
    assert p.id == "WANT"
    assert p.spoken_form
    assert p.form_status == "placeholder"


def test_all_primes_nonempty(db: LanguageDb) -> None:
    assert len(db.all_primes()) >= 60


def test_lexeme_search(db: LanguageDb) -> None:
    hits = db.search_lexemes("who")
    assert hits
    assert hits[0].gloss.lower().startswith("interrogative") or "who" in hits[0].gloss


def test_missing_prime_returns_none(db: LanguageDb) -> None:
    assert db.get_prime("NOPE") is None


def test_search_exact_match_ranks_first(db: LanguageDb) -> None:
    assert db.search_lexemes("who")[0].phon_form == "manu"


def test_search_matches_sense_gloss(db: LanguageDb) -> None:
    hits = db.search_lexemes("interrogative person")
    assert "manu" in [h.phon_form for h in hits]


def test_search_treats_wildcards_literally(db: LanguageDb) -> None:
    assert db.search_lexemes("%") == []
    assert db.search_lexemes("_") == []


def test_search_filters_by_root_class(db: LanguageDb) -> None:
    hits = db.search_lexemes("", limit=100, root_class="particle")
    assert hits
    assert {h.root_class for h in hits} == {"particle"}


def test_browse_all_is_ordered_by_frequency(db: LanguageDb) -> None:
    freqs = [lx.frequency for lx in db.browse_lexemes(limit=1000)]
    assert freqs == sorted(freqs, reverse=True)


def test_browse_one_class_matches_counts(db: LanguageDb) -> None:
    counts = db.root_class_counts()
    for root_class, n in counts.items():
        assert len(db.browse_lexemes(root_class, limit=1000)) == n
    assert sum(counts.values()) == len(db.browse_lexemes(limit=1000))


def test_get_lexeme_by_id(db: LanguageDb) -> None:
    lx = db.get_lexeme(1)
    assert lx is not None
    assert lx.phon_form == "manu"
    assert lx.form_status == "provisional"
    assert db.get_lexeme(-1) is None


def test_senses_are_ordered_and_decompositions_are_placeholders(db: LanguageDb) -> None:
    senses = db.senses_for(1)
    assert [s.sense_no for s in senses] == sorted(s.sense_no for s in senses)
    assert senses
    assert all(s.primes == () for s in senses)
    assert all(s.decomp_status == "placeholder" for s in senses)


def test_signs_for_lexeme_without_signs_is_empty(db: LanguageDb) -> None:
    assert db.signs_for(2) == []


def test_tactile_seed_sign_stays_on_the_first_lexeme(db: LanguageDb) -> None:
    # The tactile seed attaches its placeholder sign to the lowest lexeme ID.
    signs = db.signs_for(1)
    assert len(signs) == 1
    assert signs[0].hamnosys == ""
    assert signs[0].form_status == "placeholder"


# --- edge cases on a scratch database ------------------------------------
#
# The scratch file has a multi-sense lexeme, a click form, a sign with a
# nonmanual field, and one sense per status. The real seed never has these,
# so the tests exercise the query paths directly.

_PRIMES = [
    ("SOMEONE", "someone"),
    ("DO", "do"),
]

_LEXEMES = [
    (1, "mel", None, None, "speak", "verb", 300, "provisional"),
    (2, "tao", None, None, "water", "noun", 800, "provisional"),
    (3, "ʘu", "ʘ", None, "near", "modifier", 400, "provisional"),
]

_SENSES = [
    (1, 1, 1, "{}", "placeholder", "to talk"),
    (2, 2, 1, "{}", "signed_off", "liquid to drink"),
    (
        3,
        2,
        2,
        '{"primes": ["SOMEONE", "DO"], "combinators": []}',
        "placeholder",
        "large body of water",
    ),
    (4, 3, 1, "{}", "placeholder", "close by"),
]


@pytest.fixture()
def scratch_path(tmp_path: Path, repo_root: Path) -> Path:
    path = tmp_path / "scratch.sqlite"
    conn = sqlite3.connect(path)
    try:
        conn.executescript((repo_root / "language" / "schema.sql").read_text(encoding="utf-8"))
        for pid, gloss in _PRIMES:
            conn.execute(
                "INSERT INTO primes (id, gloss, category, combinators, spoken_form,"
                " signed_form, tactile_form, nsm_version) VALUES (?, ?, 'x', '[]', ?, 's', 't', 'v')",
                (pid, gloss, gloss),
            )
        conn.executemany(
            "INSERT INTO lexemes (id, phon_form, click, tone, gloss, root_class, frequency, form_status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            _LEXEMES,
        )
        conn.executemany(
            "INSERT INTO senses (id, lexeme_id, sense_no, prime_decomp, decomp_status, gloss)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(i, lx, no, dec, st, gl) for i, lx, no, dec, st, gl in _SENSES],
        )
        conn.execute(
            "INSERT INTO signs (id, lexeme_id, hamnosys, nonmanual, form_status)"
            " VALUES (1, 2, 'hn', '{\"face\": \"x\"}', 'signed_off')"
        )
        conn.commit()
    finally:
        conn.close()
    return path


def test_search_ignores_case_and_surrounding_space(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        assert [h.phon_form for h in db.search_lexemes("  WATER  ")] == ["tao"]


def test_search_lists_a_lexeme_once_when_several_senses_match(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        ids = [h.id for h in db.search_lexemes("o", limit=50)]
    assert ids.count(2) == 1
    assert len(ids) == len(set(ids))


def test_search_matches_a_click_form(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        assert [h.id for h in db.search_lexemes("ʘ")] == [3]


def test_search_in_an_unknown_root_class_is_empty(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        assert db.search_lexemes("water", root_class="adjective") == []
        assert db.browse_lexemes("adjective") == []


def test_limits_are_respected(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        assert len(db.search_lexemes("", limit=2)) == 2
        assert db.search_lexemes("", limit=0) == []
        assert len(db.browse_lexemes(limit=1)) == 1


def test_senses_are_ordered_and_carry_their_primes(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        senses = db.senses_for(2)
    assert [s.sense_no for s in senses] == [1, 2]
    assert senses[0].primes == ()
    assert senses[0].decomp_status == "signed_off"
    assert senses[1].primes == ("SOMEONE", "DO")


def test_signs_carry_status_and_nonmanual_morphemes(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        signs = db.signs_for(2)
    assert len(signs) == 1
    assert signs[0].hamnosys == "hn"
    assert signs[0].nonmanual == {"face": "x"}
    assert signs[0].form_status == "signed_off"


def test_root_class_counts_on_a_small_database(scratch_path: Path) -> None:
    with LanguageDb(scratch_path) as db:
        assert db.root_class_counts() == {"modifier": 1, "noun": 1, "verb": 1}


def test_schema_rejects_an_unknown_status(scratch_path: Path) -> None:
    conn = sqlite3.connect(scratch_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE lexemes SET form_status = 'approved' WHERE id = 1")
    finally:
        conn.close()


def test_schema_rejects_a_repeated_sense_number(scratch_path: Path) -> None:
    conn = sqlite3.connect(scratch_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO senses (lexeme_id, sense_no, prime_decomp, decomp_status, gloss)"
                " VALUES (2, 1, '{}', 'placeholder', 'again')"
            )
    finally:
        conn.close()
