"""parity_compare: cross-platform diff gate over parity_runner reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import parity_compare


def _report(got_by_case: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": [{"case_id": cid, "got": got} for cid, got in got_by_case.items()],
    }


def _got(text: str, backend: str = "native") -> dict[str, Any]:
    return {
        "request_id": "volatile",
        "pivot": {"text": text},
        "failover_events": [{"component": "x", "t": 1.0}],
        "modalities": {"spoken": {"backend": backend, "audio_path": "/x.wav", "duration_ms": 5}},
    }


def test_identical_reports_are_clean() -> None:
    py = _report({"a": _got("hi")})
    kt = _report({"a": _got("hi")})
    result = parity_compare.compare(py, kt, None)
    assert result["clean"] is True
    assert result["total_cases"] == 1
    assert result["android_present"] is False


def test_volatile_fields_are_ignored() -> None:
    py = _report({"a": _got("hi", backend="espeak")})
    an = _report({"a": _got("hi", backend="android")})
    assert parity_compare.compare(py, None, an)["clean"] is True


def test_pivot_difference_is_flagged() -> None:
    py = _report({"a": _got("hi")})
    kt = _report({"a": _got("bye")})
    result = parity_compare.compare(py, kt, None)
    assert result["clean"] is False
    assert result["diffs"] == [{"case_id": "a", "diffs": ["python_vs_kotlin"]}]


def test_missing_side_is_not_a_diff() -> None:
    py = _report({"a": _got("hi")})
    result = parity_compare.compare(py, None, None)
    assert result["clean"] is True
    assert result["kotlin_present"] is False


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert parity_compare._load(tmp_path / "nope.json") is None
    assert parity_compare._load(None) is None


def test_main_writes_report_and_exits_zero(tmp_path: Path) -> None:
    py = tmp_path / "py.json"
    kt = tmp_path / "kt.json"
    py.write_text(json.dumps(_report({"a": _got("hi")})), encoding="utf-8")
    kt.write_text(json.dumps(_report({"a": _got("hi")})), encoding="utf-8")
    out = tmp_path / "diff.json"
    rc = parity_compare.main(["--python", str(py), "--kotlin", str(kt), "--out", str(out)])
    assert rc == 0
    assert json.loads(out.read_text(encoding="utf-8"))["clean"] is True


def test_main_exits_nonzero_and_prints_diffs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    py = tmp_path / "py.json"
    an = tmp_path / "an.json"
    py.write_text(json.dumps(_report({"a": _got("hi")})), encoding="utf-8")
    an.write_text(json.dumps(_report({"a": _got("bye")})), encoding="utf-8")
    rc = parity_compare.main(["--python", str(py), "--android", str(an), "--json"])
    assert rc == 1
    assert "DIFF a" in capsys.readouterr().err
