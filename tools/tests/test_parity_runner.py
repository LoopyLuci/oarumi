"""Parity runner: schema, cases, gold comparison, missing-gold behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import parity_runner


@pytest.fixture()
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "parity"
    corpus_dir = root / "data" / "parity-basic"
    corpus_dir.mkdir(parents=True)

    (corpus_dir / "case_hello.json").write_text(
        json.dumps(
            {
                "request": {"text": "hola", "lang": "es", "modality": "spoken"},
                # no expected => not-compared path
            }
        )
    )
    (corpus_dir / "case_yes.json").write_text(
        json.dumps(
            {
                "request": {"text": "sí", "lang": "es", "modality": "spoken"},
            }
        )
    )

    monkeypatch.setattr(parity_runner, "PARITY_DATA", root / "data")
    return corpus_dir


def test_run_produces_valid_report(corpus: Path, language_db: Path) -> None:
    del corpus
    result = parity_runner.run("parity-basic", db_path=language_db, target="python", strict=False)
    assert result["target"] == "python"
    assert result["corpus"] == "parity-basic"
    assert result["total"] == 2
    assert result["passed"] == 2
    assert result["failed"] == 0
    for case in result["cases"]:
        assert "case_id" in case
        assert "got" in case
        assert case["got"] is not None
        assert case["got"]["pivot"]["text"]


def test_missing_corpus_reports_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parity_runner, "PARITY_DATA", tmp_path / "nope")
    result = parity_runner.run("nonexistent")
    assert result["total"] == 0
    assert "error" in result


def test_strict_mode_fails_on_missing_gold(corpus: Path, language_db: Path) -> None:
    del corpus
    result = parity_runner.run("parity-basic", db_path=language_db, strict=True)
    assert result["failed"] == 2


def test_cli_writes_out_file(
    corpus: Path, language_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del corpus
    out = tmp_path / "report.json"
    rc = parity_runner.main(
        [
            "--corpus",
            "parity-basic",
            "--db",
            str(language_db),
            "--out",
            str(out),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["total"] == 2
