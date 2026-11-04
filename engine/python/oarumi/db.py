"""Read-only access to the canonical language SQLite database."""

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


@dataclass(slots=True, frozen=True)
class Lexeme:
    id: int
    phon_form: str
    click: str | None
    tone: str | None
    gloss: str
    root_class: str
    frequency: int


@dataclass(slots=True, frozen=True)
class Sign:
    id: int
    lexeme_id: int
    hamnosys: str
    nonmanual: dict[str, object]


@dataclass(slots=True, frozen=True)
class TactileConstruction:
    id: int
    sign_id: int
    protocol: dict[str, object]


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
                      tactile_form, nsm_version
               FROM primes WHERE id = ?""",
            (pid,),
        ).fetchone()
        return self._row_to_prime(row) if row is not None else None

    def all_primes(self) -> list[Prime]:
        rows = self._conn.execute(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version FROM primes ORDER BY id"""
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
        )

    # --- lexemes --------------------------------------------------------

    def search_lexemes(self, query: str, limit: int = 20) -> list[Lexeme]:
        like = f"%{query}%"
        rows = self._conn.execute(
            """SELECT id, phon_form, click, tone, gloss, root_class, frequency
               FROM lexemes
               WHERE phon_form LIKE ? OR gloss LIKE ?
               ORDER BY frequency DESC, id ASC
               LIMIT ?""",
            (like, like, limit),
        ).fetchall()
        return [
            Lexeme(
                id=int(r["id"]),
                phon_form=str(r["phon_form"]),
                click=r["click"],
                tone=r["tone"],
                gloss=str(r["gloss"]),
                root_class=str(r["root_class"]),
                frequency=int(r["frequency"]),
            )
            for r in rows
        ]

    def get_lexeme_by_phon(self, phon: str) -> Lexeme | None:
        row = self._conn.execute(
            """SELECT id, phon_form, click, tone, gloss, root_class, frequency
               FROM lexemes WHERE phon_form = ?""",
            (phon,),
        ).fetchone()
        if row is None:
            return None
        return Lexeme(
            id=int(row["id"]),
            phon_form=str(row["phon_form"]),
            click=row["click"],
            tone=row["tone"],
            gloss=str(row["gloss"]),
            root_class=str(row["root_class"]),
            frequency=int(row["frequency"]),
        )

    # --- signs / tactile ------------------------------------------------

    def get_sign(self, lexeme_id: int) -> Sign | None:
        row = self._conn.execute(
            "SELECT id, lexeme_id, hamnosys, nonmanual FROM signs WHERE lexeme_id = ?",
            (lexeme_id,),
        ).fetchone()
        if row is None:
            return None
        return Sign(
            id=int(row["id"]),
            lexeme_id=int(row["lexeme_id"]),
            hamnosys=str(row["hamnosys"]),
            nonmanual=json.loads(row["nonmanual"]),
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
