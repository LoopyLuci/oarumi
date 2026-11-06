"""Seed the Oarumi language DB from language/ YAML and CSV. Idempotent.

Placeholders are explicit: a prime's spoken form and a sense's decomposition
stay marked as placeholder until a linguist signs them off. See docs/DICTIONARY.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / "language"

ROOT_CLASSES = ("noun", "verb", "modifier", "particle")
FORM_STATUSES = ("placeholder", "provisional", "signed_off")


def _status(value: str, where: str) -> str:
    if value not in FORM_STATUSES:
        raise ValueError(f"{where}: form_status {value!r} is not one of {FORM_STATUSES}")
    return value


def _insert_primes(conn: sqlite3.Connection) -> int:
    data = yaml.safe_load((LANG / "primes.yaml").read_text(encoding="utf-8"))
    version = data["nsm_version"]
    n = 0
    for p in data["primes"]:
        conn.execute(
            """
            INSERT OR IGNORE INTO primes
              (id, gloss, category, combinators, spoken_form, signed_form,
               tactile_form, nsm_version, form_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"],
                p["gloss"],
                p["category"],
                json.dumps(p["combinators"]),
                # Placeholder: the lowercased ID stands in until the linguist sets the
                # spoken form (docs/DICTIONARY.md, section 5). The Dictionary marks it pending.
                p.get("spoken_form", p["id"].lower().replace("_", "-")),
                p.get("signed_form", f"sign:{p['id'].lower()}"),
                p.get("tactile_form", f"tac:{p['id'].lower()}"),
                version,
                _status(p.get("form_status", "placeholder"), f"prime {p['id']}"),
            ),
        )
        n += 1
    return n


def _insert_lexicon(conn: sqlite3.Connection) -> int:
    """Load lexicon.csv. Columns: id, phon_form, click, tone, gloss, root_class,
    frequency, sense_gloss, and optional sense_no, primes, decomp_status, form_status.

    One row is one sense. A second row with the same phon_form adds a sense to the
    existing lexeme, numbered by sense_no (default 1). Primes is a space-separated
    list of prime IDs; empty means the decomposition is still a placeholder.
    """
    path = LANG / "lexicon.csv"
    if not path.exists():
        return 0
    prime_ids = {r[0] for r in conn.execute("SELECT id FROM primes")}
    n = 0
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            where = f"lexicon row {row['id']} ({row['phon_form']})"
            if row["root_class"] not in ROOT_CLASSES:
                raise ValueError(
                    f"{where}: root_class {row['root_class']!r} is not one of {ROOT_CLASSES}"
                )
            conn.execute(
                """
                INSERT OR IGNORE INTO lexemes
                  (id, phon_form, click, tone, gloss, root_class, frequency, form_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["id"]),
                    row["phon_form"],
                    row["click"] or None,
                    row["tone"] or None,
                    row["gloss"],
                    row["root_class"],
                    int(row.get("frequency") or 0),
                    _status(row.get("form_status") or "provisional", where),
                ),
            )
            lexeme_id = conn.execute(
                "SELECT id FROM lexemes WHERE phon_form = ?", (row["phon_form"],)
            ).fetchone()[0]
            primes = (row.get("primes") or "").split()
            unknown = [p for p in primes if p not in prime_ids]
            if unknown:
                raise ValueError(f"{where}: unknown prime(s) {unknown}")
            conn.execute(
                """
                INSERT OR IGNORE INTO senses
                  (lexeme_id, sense_no, prime_decomp, decomp_status, gloss)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    lexeme_id,
                    int(row.get("sense_no") or 1),
                    json.dumps({"primes": primes, "combinators": []}),
                    _status(row.get("decomp_status") or "placeholder", where),
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
        SELECT 1, id, '', '{}' FROM lexemes ORDER BY id LIMIT 1
        """)
    sign_row = conn.execute("SELECT id FROM signs ORDER BY id LIMIT 1").fetchone()
    if sign_row is None:
        return 0
    sign_id = sign_row[0]
    conn.execute("DELETE FROM tactile")  # this table is owned by the seed, so a re-run replaces it
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
