"""Read-only access to the canonical language SQLite database.

Entry model and status vocabulary: docs/DICTIONARY.md. The Kotlin JVM layer
(engine/kotlin LanguageDb) and the Room layer (android data/db) mirror these
methods; docs/PARITY_API.md lists them.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


@dataclass(slots=True, frozen=True)
class Prime:
    id: str
    gloss: str
    category: str
    combinators: tuple[str, ...]
    spoken_form: str
    signed_form: str
    tactile_form: str
    nsm_version: str
    form_status: str = "placeholder"


@dataclass(slots=True, frozen=True)
class Lexeme:
    id: int
    phon_form: str
    click: str | None
    tone: str | None
    gloss: str
    root_class: str
    frequency: int
    form_status: str = "provisional"


@dataclass(slots=True, frozen=True)
class Sense:
    id: int
    lexeme_id: int
    sense_no: int
    gloss: str
    primes: tuple[str, ...]
    decomp_status: str


@dataclass(slots=True, frozen=True)
class Sign:
    id: int
    lexeme_id: int
    hamnosys: str
    nonmanual: dict[str, object]
    form_status: str = "placeholder"


@dataclass(slots=True, frozen=True)
class TactileConstruction:
    id: int
    sign_id: int
    protocol: dict[str, object]


_LEXEME_COLUMNS = "id, phon_form, click, tone, gloss, root_class, frequency, form_status"


def _like_pattern(text: str) -> str:
    """Substring pattern for LIKE ... ESCAPE '\\', with % and _ taken literally."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class LanguageDb:
    """Owns a single read-only SQLite connection. Callers must close()."""

    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"language DB not found: {path}")
        uri = f"file:{path}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> LanguageDb:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- primes ---------------------------------------------------------

    def get_prime(self, pid: str) -> Prime | None:
        row = self._conn.execute(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version, form_status
               FROM primes WHERE id = ?""",
            (pid,),
        ).fetchone()
        return self._row_to_prime(row) if row is not None else None

    def all_primes(self) -> list[Prime]:
        rows = self._conn.execute(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version, form_status FROM primes ORDER BY id"""
        ).fetchall()
        return [self._row_to_prime(r) for r in rows]

    @staticmethod
    def _row_to_prime(row: sqlite3.Row) -> Prime:
        return Prime(
            id=str(row["id"]),
            gloss=str(row["gloss"]),
            category=str(row["category"]),
            combinators=tuple(json.loads(row["combinators"])),
            spoken_form=str(row["spoken_form"]),
            signed_form=str(row["signed_form"]),
            tactile_form=str(row["tactile_form"]),
            nsm_version=str(row["nsm_version"]),
            form_status=str(row["form_status"]),
        )

    # --- lexemes --------------------------------------------------------

    def search_lexemes(
        self, query: str, limit: int = 20, root_class: str | None = None
    ) -> list[Lexeme]:
        """Match phon_form, the lexeme gloss, or any sense gloss.

        Exact matches (case-insensitive) rank first, then frequency, then id.
        Surrounding whitespace is ignored.
        """
        query = query.strip()
        like = _like_pattern(query)
        rows = self._conn.execute(
            r"""SELECT id, phon_form, click, tone, gloss, root_class, frequency, form_status
                FROM lexemes
                WHERE (phon_form LIKE ? ESCAPE '\' OR gloss LIKE ? ESCAPE '\'
                       OR id IN (SELECT lexeme_id FROM senses WHERE gloss LIKE ? ESCAPE '\'))
                  AND (? IS NULL OR root_class = ?)
                ORDER BY CASE WHEN LOWER(phon_form) = LOWER(?) OR LOWER(gloss) = LOWER(?)
                              THEN 0 ELSE 1 END,
                         frequency DESC, id ASC
                LIMIT ?""",
            (like, like, like, root_class, root_class, query, query, limit),
        ).fetchall()
        return [self._row_to_lexeme(r) for r in rows]

    def get_lexeme_by_phon(self, phon: str) -> Lexeme | None:
        row = self._conn.execute(
            f"SELECT {_LEXEME_COLUMNS} FROM lexemes WHERE phon_form = ?",
            (phon,),
        ).fetchone()
        return self._row_to_lexeme(row) if row is not None else None

    def get_lexeme(self, lexeme_id: int) -> Lexeme | None:
        row = self._conn.execute(
            f"SELECT {_LEXEME_COLUMNS} FROM lexemes WHERE id = ?",
            (lexeme_id,),
        ).fetchone()
        return self._row_to_lexeme(row) if row is not None else None

    def browse_lexemes(self, root_class: str | None = None, limit: int = 200) -> list[Lexeme]:
        """Lexemes of one root class, or of every class when root_class is None."""
        rows = self._conn.execute(
            f"""SELECT {_LEXEME_COLUMNS} FROM lexemes
                WHERE (? IS NULL OR root_class = ?)
                ORDER BY frequency DESC, id ASC
                LIMIT ?""",
            (root_class, root_class, limit),
        ).fetchall()
        return [self._row_to_lexeme(r) for r in rows]

    def root_class_counts(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT root_class, COUNT(*) AS n FROM lexemes GROUP BY root_class ORDER BY root_class"
        ).fetchall()
        return {str(r["root_class"]): int(r["n"]) for r in rows}

    @staticmethod
    def _row_to_lexeme(row: sqlite3.Row) -> Lexeme:
        return Lexeme(
            id=int(row["id"]),
            phon_form=str(row["phon_form"]),
            click=row["click"],
            tone=row["tone"],
            gloss=str(row["gloss"]),
            root_class=str(row["root_class"]),
            frequency=int(row["frequency"]),
            form_status=str(row["form_status"]),
        )

    # --- senses ---------------------------------------------------------

    def senses_for(self, lexeme_id: int) -> list[Sense]:
        rows = self._conn.execute(
            """SELECT id, lexeme_id, sense_no, gloss, prime_decomp, decomp_status
               FROM senses WHERE lexeme_id = ? ORDER BY sense_no, id""",
            (lexeme_id,),
        ).fetchall()
        return [
            Sense(
                id=int(r["id"]),
                lexeme_id=int(r["lexeme_id"]),
                sense_no=int(r["sense_no"]),
                gloss=str(r["gloss"]),
                # A decomposition without a "primes" array reads as empty, not as an error.
                primes=tuple(json.loads(r["prime_decomp"]).get("primes", [])),
                decomp_status=str(r["decomp_status"]),
            )
            for r in rows
        ]

    # --- signs / tactile ------------------------------------------------

    def get_sign(self, lexeme_id: int) -> Sign | None:
        row = self._conn.execute(
            "SELECT id, lexeme_id, hamnosys, nonmanual, form_status FROM signs "
            "WHERE lexeme_id = ? ORDER BY id LIMIT 1",
            (lexeme_id,),
        ).fetchone()
        return self._row_to_sign(row) if row is not None else None

    def signs_for(self, lexeme_id: int) -> list[Sign]:
        rows = self._conn.execute(
            "SELECT id, lexeme_id, hamnosys, nonmanual, form_status FROM signs "
            "WHERE lexeme_id = ? ORDER BY id",
            (lexeme_id,),
        ).fetchall()
        return [self._row_to_sign(r) for r in rows]

    @staticmethod
    def _row_to_sign(row: sqlite3.Row) -> Sign:
        return Sign(
            id=int(row["id"]),
            lexeme_id=int(row["lexeme_id"]),
            hamnosys=str(row["hamnosys"]),
            nonmanual=json.loads(row["nonmanual"]),
            form_status=str(row["form_status"]),
        )

    def tactile_for_sign(self, sign_id: int) -> list[TactileConstruction]:
        rows = self._conn.execute(
            "SELECT id, sign_id, protocol_json FROM tactile WHERE sign_id = ?",
            (sign_id,),
        ).fetchall()
        return [
            TactileConstruction(
                id=int(r["id"]),
                sign_id=int(r["sign_id"]),
                protocol=json.loads(r["protocol_json"]),
            )
            for r in rows
        ]

    # --- gold -----------------------------------------------------------

    def get_gold(self, component: str, input_hash: str) -> dict[str, object] | None:
        row = self._conn.execute(
            """SELECT output_json FROM parity_gold
               WHERE component = ? AND input_hash = ?""",
            (component, input_hash),
        ).fetchone()
        if row is None:
            return None
        result: dict[str, object] = json.loads(row["output_json"])
        return result
