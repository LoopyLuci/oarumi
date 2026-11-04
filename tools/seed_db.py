"""Seed the Oarumi language DB from language/ YAML and CSV. Idempotent."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / "language"


def _insert_primes(conn: sqlite3.Connection) -> int:
    data = yaml.safe_load((LANG / "primes.yaml").read_text(encoding="utf-8"))
    version = data["nsm_version"]
    n = 0
    for p in data["primes"]:
        conn.execute(
            """
            INSERT OR IGNORE INTO primes
              (id, gloss, category, combinators, spoken_form, signed_form,
               tactile_form, nsm_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"],
                p["gloss"],
                p["category"],
                json.dumps(p["combinators"]),
                p.get("spoken_form", p["id"].lower().replace("_", "-")),
                p.get("signed_form", f"sign:{p['id'].lower()}"),
                p.get("tactile_form", f"tac:{p['id'].lower()}"),
                version,
            ),
        )
        n += 1
    return n


def _insert_lexicon(conn: sqlite3.Connection) -> int:
    path = LANG / "lexicon.csv"
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            conn.execute(
                """
                INSERT OR IGNORE INTO lexemes
                  (id, phon_form, click, tone, gloss, root_class, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["id"]),
                    row["phon_form"],
                    row["click"] or None,
                    row["tone"] or None,
                    row["gloss"],
                    row["root_class"],
                    int(row.get("frequency") or 0),
                ),
            )
            lexeme_id = conn.execute(
                "SELECT id FROM lexemes WHERE phon_form = ?", (row["phon_form"],)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO senses (lexeme_id, prime_decomp, gloss) VALUES (?, ?, ?)",
                (
                    lexeme_id,
                    json.dumps({"primes": [], "combinators": []}),
                    row.get("sense_gloss") or row["gloss"],
                ),
            )
            n += 1
    return n


def _insert_tactile(conn: sqlite3.Connection) -> int:
    path = LANG / "tactile" / "protactile.yaml"
    if not path.exists():
        return 0
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # Seed tactile rows against a synthetic sign to keep FK integrity.
    conn.execute("""
        INSERT OR IGNORE INTO signs (id, lexeme_id, hamnosys, nonmanual)
        SELECT 1, id, '', '{}' FROM lexemes LIMIT 1
        """)
    sign_row = conn.execute("SELECT id FROM signs LIMIT 1").fetchone()
    if sign_row is None:
        return 0
    sign_id = sign_row[0]
    n = 0
    for c in data.get("constructions", []):
        conn.execute(
            "INSERT INTO tactile (sign_id, protocol_json) VALUES (?, ?)",
            (sign_id, json.dumps(c)),
        )
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(LANG / "oarumi.db"))
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        p = _insert_primes(conn)
        lx = _insert_lexicon(conn)
        tc = _insert_tactile(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"OK   seeded primes={p} lexemes={lx} tactile={tc} -> {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
