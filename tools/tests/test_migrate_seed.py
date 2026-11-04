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
    monkeypatch.setattr(migrate, "SCHEMA", schema)
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
