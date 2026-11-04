"""Freeze tools write parity gold. Tests redirect every output into a temp copy."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import freeze_gold, freeze_renderer_gold

ROOT = Path(__file__).resolve().parents[2]
REAL_RENDERERS = ROOT / "tests" / "parity" / "data" / "renderers"
REAL_BASIC = ROOT / "tests" / "parity" / "data" / "parity-basic"


@pytest.fixture()
def renderer_fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fixtures = tmp_path / "renderers"
    shutil.copytree(REAL_RENDERERS, fixtures)
    monkeypatch.setattr(freeze_renderer_gold, "FIXTURES", fixtures)
    return fixtures


def test_freeze_tts_writes_one_gold_per_case(renderer_fixtures: Path) -> None:
    n = freeze_renderer_gold.freeze_tts()
    written = list((renderer_fixtures / "tts" / "gold").glob("*.json"))
    assert n > 0
    assert len(written) == n
    first = json.loads(written[0].read_text(encoding="utf-8"))
    assert "audio_path" not in first


def test_freeze_sign_writes_one_gold_per_case(renderer_fixtures: Path) -> None:
    n = freeze_renderer_gold.freeze_sign()
    assert n > 0
    assert len(list((renderer_fixtures / "sign" / "gold").glob("*.json"))) == n


def test_freeze_tactile_writes_one_gold_per_case(renderer_fixtures: Path) -> None:
    n = freeze_renderer_gold.freeze_tactile()
    assert n > 0
    assert len(list((renderer_fixtures / "tactile" / "gold").glob("*.json"))) == n


def test_renderer_main_reports_counts(
    renderer_fixtures: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert freeze_renderer_gold.main() == 0
    assert "froze tts=" in capsys.readouterr().out


@pytest.fixture()
def pipeline_fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    corpus_root = tmp_path / "data"
    corpus = corpus_root / "parity-basic"
    corpus.mkdir(parents=True)
    for src in sorted(REAL_BASIC.glob("*.json"))[:2]:
        shutil.copy(src, corpus / src.name)
    db = tmp_path / "oarumi.db"
    shutil.copy(ROOT / "language" / "oarumi.db", db)
    monkeypatch.setattr(freeze_gold, "PARITY_DATA", corpus_root)
    return corpus, db


def test_freeze_pipeline_writes_expected_and_gold_rows(
    pipeline_fixtures: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, db = pipeline_fixtures
    assert freeze_gold.main(["--db", str(db), "--corpus", "parity-basic"]) == 0
    assert "froze 2 pipeline gold output(s)" in capsys.readouterr().out
    for case_path in corpus.glob("*.json"):
        assert "expected" in json.loads(case_path.read_text(encoding="utf-8"))

    import sqlite3

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM parity_gold WHERE component='pipeline'")
        assert rows.fetchone()[0] >= 2
    finally:
        conn.close()


def test_freeze_pipeline_dry_run_leaves_files_alone(
    pipeline_fixtures: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, db = pipeline_fixtures
    before = {p.name: p.read_text(encoding="utf-8") for p in corpus.glob("*.json")}
    assert freeze_gold.main(["--db", str(db), "--dry-run"]) == 0
    assert "DRY" in capsys.readouterr().out
    after = {p.name: p.read_text(encoding="utf-8") for p in corpus.glob("*.json")}
    assert before == after


def test_missing_corpus_fails(
    pipeline_fixtures: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, db = pipeline_fixtures
    assert freeze_gold.main(["--db", str(db), "--corpus", "absent"]) == 2
    assert "corpus not found" in capsys.readouterr().err


def test_unknown_component_fails(
    pipeline_fixtures: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, db = pipeline_fixtures
    assert freeze_gold.main(["--db", str(db), "--component", "hologram"]) == 2
    assert "unknown component" in capsys.readouterr().err


def test_component_delegates_to_renderer_freezer(
    renderer_fixtures: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert freeze_gold.main(["--component", "tactile"]) == 0
    assert "froze tactile gold" in capsys.readouterr().out


def test_canonical_strips_volatile_fields() -> None:
    result = {
        "request_id": "x",
        "failover_events": [{"component": "c", "t": 1.0}],
        "modalities": {"spoken": {"backend": "espeak", "audio_path": "/a", "duration_ms": 3}},
    }
    out = freeze_gold._canonical(result)
    assert "request_id" not in out
    assert out["failover_events"] == [{"component": "c"}]
    assert out["modalities"]["spoken"] == {"backend": "native"}
