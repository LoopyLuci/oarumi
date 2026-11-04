"""Schema drift detection: field paths, clean runs, synthetic drift."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import schema_export


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    import yaml

    path.write_text(yaml.safe_dump(obj))


def _write_schema(path: Path, schema: dict[str, Any]) -> None:
    path.write_text(json.dumps(schema, indent=2))


def test_repo_is_clean() -> None:
    # The repository as shipped must have no drift.
    assert schema_export.check_drift() == []


def test_detects_new_top_level_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lang = tmp_path / "language"
    schemas = lang / "schemas"
    (lang / "signs").mkdir(parents=True)
    (lang / "tactile").mkdir(parents=True)
    schemas.mkdir()

    _write_yaml(
        lang / "primes.yaml",
        {
            "nsm_version": "x",
            "primes": [{"id": "A", "category": "c", "gloss": "g", "combinators": ["c"]}],
            "new_top": "unexpected",
        },
    )
    _write_schema(
        schemas / "primes.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "nsm_version": {"type": "string"},
                "primes": {"type": "array"},
            },
            "additionalProperties": False,
        },
    )

    # Provide the other YAML/schema pairs so check_drift does not fail on them.
    for stem, name in (
        ("phonology", "phonology.schema.json"),
        ("morphology", "morphology.schema.json"),
        ("syntax", "syntax.schema.json"),
        ("prosody", "prosody.schema.json"),
        ("signs/classifiers", "classifiers.schema.json"),
        ("tactile/protactile", "protactile.schema.json"),
    ):
        _write_yaml(lang / f"{stem}.yaml", {"k": "v"})
        _write_schema(
            schemas / name,
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"k": {"type": "string"}},
                "additionalProperties": False,
            },
        )

    monkeypatch.setattr(schema_export, "LANG", lang)
    monkeypatch.setattr(schema_export, "SCHEMAS", schemas)

    problems = schema_export.check_drift()
    assert any("new_top" in p for p in problems)


def test_list_fields_runs(capsys: pytest.CaptureFixture[str]) -> None:
    rc = schema_export.main(["--list"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "primes" in captured.out
