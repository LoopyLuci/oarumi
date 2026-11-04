"""Targeted tests for branches not reached by the feature tests (pivot, DB, pipeline)."""

from __future__ import annotations

import sqlite3
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.errors import CapabilityMissingError, FallbackRequired, OfflineError
from oarumi.pivot.argos_adapter import ArgosAdapter
from oarumi.pivot.translator import PivotTranslator


class _Lang:
    def __init__(self, code: str) -> None:
        self.code = code


def _fake_argos(
    monkeypatch: pytest.MonkeyPatch,
    langs: list[str],
    translate: object,
) -> None:
    pkg = types.ModuleType("argostranslate")
    mod = types.ModuleType("argostranslate.translate")
    mod.get_installed_languages = lambda: [_Lang(c) for c in langs]  # type: ignore[attr-defined]
    mod.translate = translate  # type: ignore[attr-defined]
    pkg.translate = mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "argostranslate", pkg)
    monkeypatch.setitem(sys.modules, "argostranslate.translate", mod)


@pytest.fixture()
def no_argos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "argostranslate", None)
    monkeypatch.setitem(sys.modules, "argostranslate.translate", None)


# --- argos adapter ---------------------------------------------------------


def test_adapter_missing_package_raises_capability_error(no_argos: None) -> None:
    with pytest.raises(CapabilityMissingError):
        ArgosAdapter(offline=False).translate("hola", "es")


def test_adapter_available_false_when_package_missing(no_argos: None) -> None:
    assert ArgosAdapter(offline=False).available("es") is False


def test_adapter_offline_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = ArgosAdapter(offline=True)
    with pytest.raises(OfflineError):
        adapter.available("es")
    with pytest.raises(OfflineError):
        adapter.translate("hola", "es")


def test_adapter_available_checks_installed_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_argos(monkeypatch, ["es", "en"], lambda t, s, d: t)
    adapter = ArgosAdapter(offline=False)
    assert adapter.available("es", "en") is True
    assert adapter.available("de", "en") is False


def test_adapter_translate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_argos(monkeypatch, ["es", "en"], lambda t, s, d: f"{t}!")
    assert ArgosAdapter(offline=False).translate("hola", "es") == "hola!"


def test_adapter_translate_wraps_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(t: str, s: str, d: str) -> str:
        raise RuntimeError("model crashed")

    _fake_argos(monkeypatch, ["es", "en"], boom)
    with pytest.raises(CapabilityMissingError, match="model crashed"):
        ArgosAdapter(offline=False).translate("hola", "es")


# --- pivot translator ------------------------------------------------------


def _cfg(offline: bool) -> EngineConfig:
    return EngineConfig(
        home=Path("."), strict_parity=False, dev_models=True, offline=offline, log_level="INFO"
    )


def test_translator_empty_and_same_language_passthrough() -> None:
    t = PivotTranslator(cfg=_cfg(offline=True))
    assert t.translate("   ", "es").source == "passthrough"
    same = t.translate("hello", "en", "en")
    assert same.source == "passthrough"
    assert same.trace


def test_translator_uses_argos_when_online(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_argos(monkeypatch, ["es", "en"], lambda t, s, d: "hello there")
    t = PivotTranslator(cfg=_cfg(offline=False))
    out = t.translate("una frase que no está en la frasera", "es")
    assert out.source == "argos"
    assert out.text == "hello there"


def test_translator_falls_through_when_argos_unavailable(no_argos: None) -> None:
    t = PivotTranslator(cfg=_cfg(offline=False))
    with pytest.raises(FallbackRequired):
        t.translate("una frase que no está en la frasera", "es")


def test_translator_offline_skips_argos_and_falls_back() -> None:
    t = PivotTranslator(cfg=_cfg(offline=True))
    with pytest.raises(FallbackRequired):
        t.translate("una frase que no está en la frasera", "es")


# --- language DB -----------------------------------------------------------


@pytest.fixture()
def fresh_db(repo_root: Path, tmp_path: Path) -> Iterator[LanguageDb]:
    """A throwaway DB with the real schema plus one sign and one tactile row."""
    path = tmp_path / "scratch.db"
    conn = sqlite3.connect(path)
    conn.executescript((repo_root / "language" / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO lexemes (id, phon_form, click, tone, gloss, root_class, frequency)"
        " VALUES (1, 'manu', NULL, NULL, 'who', 'noun', 900)"
    )
    conn.execute(
        "INSERT INTO signs (id, lexeme_id, hamnosys, nonmanual) VALUES (1, 1, 'sym:hamx', '{}')"
    )
    conn.execute(
        'INSERT INTO tactile (id, sign_id, protocol_json) VALUES (1, 1, \'{"hand": "right"}\')'
    )
    conn.execute(
        "INSERT INTO parity_gold (component, input_hash, output_json, frozen_at)"
        " VALUES ('pipeline', 'abc', '{\"ok\": true}', '2026-01-01T00:00:00+00:00')"
    )
    conn.commit()
    conn.close()
    with LanguageDb(path) as db:
        yield db


def test_db_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LanguageDb(tmp_path / "nope.db")


def test_db_lexeme_lookup_and_sign_and_tactile(fresh_db: LanguageDb) -> None:
    lex = fresh_db.get_lexeme_by_phon("manu")
    assert lex is not None and lex.gloss == "who"
    assert fresh_db.get_lexeme_by_phon("zzz") is None

    sign = fresh_db.get_sign(1)
    assert sign is not None and sign.hamnosys == "sym:hamx"
    assert fresh_db.get_sign(99) is None

    tactile = fresh_db.tactile_for_sign(1)
    assert tactile[0].protocol == {"hand": "right"}
    assert fresh_db.tactile_for_sign(99) == []


def test_db_gold_roundtrip(fresh_db: LanguageDb) -> None:
    assert fresh_db.get_gold("pipeline", "abc") == {"ok": True}
    assert fresh_db.get_gold("pipeline", "missing") is None
