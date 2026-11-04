"""schema_export command-line entry points: --list, --check, and drift reporting."""

from __future__ import annotations

import pytest

from tools import schema_export


def test_list_prints_field_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert schema_export.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_check_passes_on_the_repo(capsys: pytest.CaptureFixture[str]) -> None:
    assert schema_export.main(["--check"]) == 0
    assert "no drift" in capsys.readouterr().out


def test_check_reports_drift_and_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        schema_export, "check_drift", lambda: ["phonology: field 'x.y' not declared"]
    )
    assert schema_export.main(["--check"]) == 1
    assert "DRIFT phonology" in capsys.readouterr().err
