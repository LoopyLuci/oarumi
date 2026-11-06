"""Forward-only SQLite migration runner for the Oarumi language DB."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "language" / "migrations"


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _applied(conn: sqlite3.Connection) -> dict[str, str]:
    try:
        rows = conn.execute("SELECT id, checksum FROM schema_migrations").fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r[0]: r[1] for r in rows}


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY NOT NULL,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        )
        """)
    conn.commit()


def _sql_for(path: Path) -> str:
    # Migrations are frozen once applied. schema.sql is the current full schema,
    # not a migration, so it is never executed here.
    return path.read_text(encoding="utf-8")


def apply(conn: sqlite3.Connection) -> int:
    _ensure_table(conn)
    applied = _applied(conn)
    pending: list[tuple[str, Path]] = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        mid = path.stem
        if mid not in applied:
            pending.append((mid, path))

    if not pending:
        print("OK   no pending migrations")
        return 0

    for mid, path in pending:
        sql = _sql_for(path)
        checksum = _checksum(path)
        print(f"APPLY {mid}")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at, checksum) VALUES (?, ?, ?)",
            (mid, datetime.now(UTC).isoformat(), checksum),
        )
        conn.commit()

    print(f"OK   applied {len(pending)} migration(s)")
    return 0


def status(conn: sqlite3.Connection) -> int:
    _ensure_table(conn)
    applied = _applied(conn)
    for path in sorted(MIGRATIONS.glob("*.sql")):
        mark = "applied" if path.stem in applied else "PENDING"
        print(f"{mark:8} {path.stem}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "language" / "oarumi.db"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        return apply(conn) if args.apply else status(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
