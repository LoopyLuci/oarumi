"""Canary: load, run, pass/fail decisions."""

from __future__ import annotations

import json
from pathlib import Path

from oarumi.reliability.canary import Canary


def _write_case(dir: Path, name: str, inp: dict[str, object], exp: dict[str, object]) -> None:
    (dir / f"{name}.json").write_text(json.dumps({"input": inp, "expected": exp}))


def test_no_cases_fails(tmp_path: Path) -> None:
    c = Canary(root=tmp_path)
    result = c.run("pivot", call=lambda x: x)
    assert result.passed is False
    assert "no_cases" in result.failures


def test_all_pass(tmp_path: Path) -> None:
    d = tmp_path / "pivot"
    d.mkdir()
    _write_case(d, "a", {"x": 1}, {"y": 2})
    _write_case(d, "b", {"x": 3}, {"y": 6})
    c = Canary(root=tmp_path)
    result = c.run("pivot", call=lambda i: {"y": i["x"] * 2})
    assert result.passed is True
    assert result.total == 2


def test_one_mismatch_fails(tmp_path: Path) -> None:
    d = tmp_path / "pivot"
    d.mkdir()
    _write_case(d, "a", {"x": 1}, {"y": 2})
    _write_case(d, "b", {"x": 3}, {"y": 999})
    c = Canary(root=tmp_path)
    result = c.run("pivot", call=lambda i: {"y": i["x"] * 2})
    assert result.passed is False
    assert any("b:mismatch" in f for f in result.failures)


def test_callback_raises(tmp_path: Path) -> None:
    d = tmp_path / "pivot"
    d.mkdir()
    _write_case(d, "a", {"x": 1}, {"y": 2})

    def raises(i: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("boom")

    result = Canary(root=tmp_path).run("pivot", call=raises)
    assert result.passed is False
    assert any("a:raised:RuntimeError" in f for f in result.failures)
