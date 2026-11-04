"""generate_canary: samples parity-basic cases into per-component canaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import generate_canary


def test_main_writes_three_canaries_per_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(5):
        (src / f"case_{i}.json").write_text(
            json.dumps({"request": {"text": f"t{i}"}, "expected": {"ok": i}}),
            encoding="utf-8",
        )
    dst = tmp_path / "canary"
    monkeypatch.setattr(generate_canary, "SRC", src)
    monkeypatch.setattr(generate_canary, "DST", dst)

    assert generate_canary.main() == 0
    for component in generate_canary.COMPONENTS:
        files = sorted((dst / component).glob("canary_*.json"))
        assert len(files) == 3
        body = json.loads(files[0].read_text(encoding="utf-8"))
        assert set(body) == {"input", "expected"}
    assert "wrote canaries" in capsys.readouterr().out


def test_main_warns_when_source_corpus_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(generate_canary, "SRC", tmp_path / "empty")
    monkeypatch.setattr(generate_canary, "DST", tmp_path / "canary")

    assert generate_canary.main() == 0
    assert "WARN no parity-basic cases" in capsys.readouterr().out
    assert not (tmp_path / "canary").exists()
