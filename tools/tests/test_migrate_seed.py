"""migrate and seed_db: schema application and seed population."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools import migrate, seed_db


@pytest.fixture()
def mini_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE widgets (id INTEGER PRIMARY KEY NOT NULL);\n", encoding="utf-8")
    (migrations / "0001_init.sql").write_text(schema.read_text(encoding="utf-8"), encoding="utf-8")
    (migrations / "0002_extra.sql").write_text(
        "CREATE TABLE gadgets (id INTEGER PRIMARY KEY NOT NULL);\n", encoding="utf-8"
    )
    monkeypatch.setattr(migrate, "MIGRATIONS", migrations)
    return tmp_path


def test_apply_runs_pending_migrations_once(
    mini_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    conn = sqlite3.connect(mini_repo / "db.sqlite")
    try:
        assert migrate.apply(conn) == 0
        assert "applied 2 migration(s)" in capsys.readouterr().out
        assert migrate.apply(conn) == 0
        assert "no pending migrations" in capsys.readouterr().out
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"widgets", "gadgets", "schema_migrations"} <= tables
    finally:
        conn.close()


def test_status_lists_each_migration(mini_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    conn = sqlite3.connect(mini_repo / "db.sqlite")
    try:
        migrate.apply(conn)
        (mini_repo / "migrations" / "0003_later.sql").write_text("SELECT 1;\n", encoding="utf-8")
        assert migrate.status(conn) == 0
        out = capsys.readouterr().out
        assert "applied  0001_init" in out
        assert "PENDING  0003_later" in out
    finally:
        conn.close()


def test_main_apply_and_status(mini_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = mini_repo / "nested" / "db.sqlite"
    assert migrate.main(["--db", str(db), "--apply"]) == 0
    assert db.exists()
    assert migrate.main(["--db", str(db), "--status"]) == 0
    assert "applied" in capsys.readouterr().out


def test_applied_is_empty_before_table_exists(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "fresh.sqlite")
    try:
        assert migrate._applied(conn) == {}
    finally:
        conn.close()


def test_seed_populates_primes_lexicon_and_tactile(tmp_path: Path) -> None:
    db = tmp_path / "seed.sqlite"
    conn = sqlite3.connect(db)
    try:
        migrate.apply(conn)
    finally:
        conn.close()

    assert seed_db.main(["--db", str(db)]) == 0

    conn = sqlite3.connect(db)
    try:
        primes = conn.execute("SELECT COUNT(*) FROM primes").fetchone()[0]
        lexemes = conn.execute("SELECT COUNT(*) FROM lexemes").fetchone()[0]
        senses = conn.execute("SELECT COUNT(*) FROM senses").fetchone()[0]
        assert primes > 0
        assert lexemes > 0
        assert senses == lexemes
    finally:
        conn.close()


def _migrated(tmp_path: Path) -> Path:
    db = tmp_path / "migrated.sqlite"
    conn = sqlite3.connect(db)
    try:
        migrate.apply(conn)
    finally:
        conn.close()
    return db


def _mini_lang(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lexicon: str) -> None:
    lang = tmp_path / "language"
    lang.mkdir()
    (lang / "primes.yaml").write_text(
        "nsm_version: test\n"
        "primes:\n"
        "  - { id: SOMEONE, category: substantives, gloss: someone, combinators: [substance] }\n"
        "  - { id: DO, category: mental, gloss: do, combinators: [predicate] }\n",
        encoding="utf-8",
    )
    (lang / "lexicon.csv").write_text(lexicon, encoding="utf-8")
    monkeypatch.setattr(seed_db, "LANG", lang)


_HEADER = "id,phon_form,click,tone,gloss,root_class,frequency,sense_gloss,sense_no,primes\n"


def test_seed_rejects_unknown_root_class(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _mini_lang(tmp_path, monkeypatch, _HEADER + "1,xo,,,thing,verbish,1,thing,1,\n")
    with pytest.raises(ValueError, match="root_class"):
        seed_db.main(["--db", str(_migrated(tmp_path))])


def test_seed_rejects_unknown_prime_in_decomposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mini_lang(tmp_path, monkeypatch, _HEADER + "1,xo,,,thing,noun,1,thing,1,NOPE\n")
    with pytest.raises(ValueError, match="unknown prime"):
        seed_db.main(["--db", str(_migrated(tmp_path))])


def test_seed_adds_senses_once_and_keeps_decomposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mini_lang(
        tmp_path,
        monkeypatch,
        _HEADER
        + "1,xo,,,thing,noun,1,thing,1,SOMEONE\n"
        + "1,xo,,,thing,noun,1,a second meaning,2,DO\n",
    )
    db = _migrated(tmp_path)
    assert seed_db.main(["--db", str(db)]) == 0
    assert seed_db.main(["--db", str(db)]) == 0

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT sense_no, prime_decomp, decomp_status FROM senses ORDER BY sense_no"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [
        (1, '{"primes": ["SOMEONE"], "combinators": []}', "placeholder"),
        (2, '{"primes": ["DO"], "combinators": []}', "placeholder"),
    ]


def _shape(conn: sqlite3.Connection) -> dict[str, object]:
    """Tables, columns and named indexes, independent of column order."""
    shape: dict[str, object] = {}
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    for table in tables:
        columns = {
            r[1]: (r[2], r[3], r[4], r[5]) for r in conn.execute(f"PRAGMA table_info({table})")
        }
        indexes = {}
        for r in conn.execute(f"PRAGMA index_list({table})"):
            if r[1].startswith("sqlite_autoindex"):
                continue
            indexes[r[1]] = (
                bool(r[2]),
                tuple(c[2] for c in conn.execute(f"PRAGMA index_info({r[1]})")),
            )
        shape[table] = (columns, indexes)
    return shape


def test_migrations_build_the_schema_in_schema_sql(tmp_path: Path) -> None:
    migrated = sqlite3.connect(_migrated(tmp_path))
    fresh = sqlite3.connect(tmp_path / "fresh.sqlite")
    try:
        fresh.executescript((migrate.ROOT / "language" / "schema.sql").read_text(encoding="utf-8"))
        assert _shape(migrated) == _shape(fresh)
    finally:
        migrated.close()
        fresh.close()
