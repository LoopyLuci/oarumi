"""bench_compare: regression gate against the committed baseline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import bench_compare


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _current(path: Path, means: dict[str, float]) -> Path:
    return _write(
        path,
        {
            "benchmarks": [
                {"name": f"tests/bench/test_x.py::{name}", "stats": {"mean": mean}}
                for name, mean in means.items()
            ]
        },
    )


def _baseline(path: Path, means: dict[str, float]) -> Path:
    return _write(
        path,
        {"benchmarks": [{"name": name, "mean_ms": mean} for name, mean in means.items()]},
    )


def test_within_tolerance_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cur = _current(tmp_path / "cur.json", {"fast": 0.0011})
    base = _baseline(tmp_path / "base.json", {"fast": 1.0})
    assert bench_compare.compare(cur, base, 1.20) == 0
    assert "within" in capsys.readouterr().out


def test_regression_beyond_tolerance_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cur = _current(tmp_path / "cur.json", {"slow": 0.002})
    base = _baseline(tmp_path / "base.json", {"slow": 1.0})
    assert bench_compare.compare(cur, base, 1.20) == 1
    assert "REGRESSION slow" in capsys.readouterr().err


def test_missing_current_benchmark_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cur = _current(tmp_path / "cur.json", {})
    base = _baseline(tmp_path / "base.json", {"gone": 1.0})
    assert bench_compare.compare(cur, base, 1.20) == 0
    assert "MISSING current: gone" in capsys.readouterr().err


def test_new_benchmark_is_noted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cur = _current(tmp_path / "cur.json", {"fresh": 0.5})
    base = _baseline(tmp_path / "base.json", {"old": 1.0})
    assert bench_compare.compare(cur, base, 1.20) == 0
    assert "NOTE new benchmark: fresh" in capsys.readouterr().out


def test_empty_baseline_skips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cur = _current(tmp_path / "cur.json", {"any": 9.0})
    base = _baseline(tmp_path / "base.json", {})
    assert bench_compare.compare(cur, base, 1.20) == 0
    assert "baseline empty" in capsys.readouterr().err


def test_main_parses_arguments(tmp_path: Path) -> None:
    cur = _current(tmp_path / "cur.json", {"fast": 0.001})
    base = _baseline(tmp_path / "base.json", {"fast": 1.0})
    rc = bench_compare.main(["--current", str(cur), "--baseline", str(base), "--tolerance", "1.5"])
    assert rc == 0
