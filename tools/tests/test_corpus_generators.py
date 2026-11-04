"""Corpus generators write deterministic cases. Output is redirected to a temp dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import generate_parity_complex, generate_parity_corpus


@pytest.mark.parametrize(
    ("module", "expected_min"),
    [
        (generate_parity_corpus, 200),
        (generate_parity_complex, 150),
    ],
    ids=["basic", "complex"],
)
def test_generator_writes_request_objects_deterministically(
    module: object,
    expected_min: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "out"
    monkeypatch.setattr(module, "OUT", out)

    assert module.main() == 0  # type: ignore[attr-defined]
    first = {p.name: p.read_text(encoding="utf-8") for p in out.glob("*.json")}
    assert len(first) >= expected_min

    for body in first.values():
        assert "request" in json.loads(body)

    assert module.main() == 0  # type: ignore[attr-defined]
    second = {p.name: p.read_text(encoding="utf-8") for p in out.glob("*.json")}
    assert first == second
    assert "wrote" in capsys.readouterr().out
