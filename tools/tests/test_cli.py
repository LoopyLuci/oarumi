"""End-to-end tests for the `oarumi` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import cli


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    return rc, out, err


def test_translate_human_output(
    language_db: Path, audio_assets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del language_db, audio_assets
    rc, out, err = _run(["translate", "hola", "--from", "es"], capsys)
    assert rc == 0, err
    assert "surface:" in out
    assert "hello" in out
    assert "degraded:    False" in out


def test_translate_json_output(
    language_db: Path, audio_assets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del language_db, audio_assets
    rc, out, err = _run(["translate", "hola", "--from", "es", "--json"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    for key in (
        "request_id",
        "input",
        "pivot",
        "nsm",
        "surface",
        "modalities",
        "trace",
        "failover_events",
        "degraded",
    ):
        assert key in payload
    assert payload["pivot"]["text"] == "hello"


def test_translate_rejects_non_oarumi_target(
    language_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del language_db
    rc, _, err = _run(["translate", "hola", "--from", "es", "--to", "fr"], capsys)
    assert rc == 2
    assert "only '--to oarumi'" in err


def test_decompose_ok(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    rc, out, err = _run(["decompose", "hello", "--json"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["valid"] is True
    assert any(c["head"] == "SAY" for c in payload["combinators"])


def test_decompose_unknown_returns_1(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    rc, _, err = _run(["decompose", "xyzzy plover flibbertigibbet"], capsys)
    assert rc == 1
    assert "error:" in err


def test_realize_round_trip(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    nsm_json = json.dumps(
        {
            "primes": [
                {"id": "I", "role": "agent"},
                {"id": "WANT", "role": "predicate"},
                {"id": "SOMETHING", "role": "patient"},
            ],
            "combinators": [{"type": "clause", "head": "WANT", "args": ["I", "SOMETHING"]}],
            "valid": True,
        }
    )
    rc, out, err = _run(["realize", nsm_json], capsys)
    assert rc == 0, err
    surface = json.loads(out)
    assert surface["phonemes"]
    assert surface["mood"] == "DECL"


def test_realize_bad_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc, _, err = _run(["realize", "not json"], capsys)
    assert rc == 2
    assert "bad NSM JSON" in err


def test_render_tactile(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    surface_json = json.dumps(
        {
            "phonemes": ["hello"],
            "clitics": [{"form": "=ha", "type": "mood_declarative"}],
            "mood": "DECL",
            "modality": "tactile",
        }
    )
    rc, out, err = _run(["render", surface_json, "--modality", "tactile"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["protocol"]["construction_id"] == "T001"


def test_render_spoken(
    language_db: Path, audio_assets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    del language_db, audio_assets
    surface_json = json.dumps(
        {
            "phonemes": ["ʘ", "a"],
            "clitics": [{"form": "=ha", "type": "mood_declarative"}],
            "mood": "DECL",
            "modality": "spoken",
        }
    )
    rc, out, err = _run(["render", surface_json, "--modality", "spoken"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["backend"] == "asset"
    assert Path(payload["audio_path"]).exists()


def test_route_phrasebook_hit(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    rc, out, err = _run(["route", "hola", "--lang", "es"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["kind"] == "direct_deterministic"


def test_route_unsupported_language(language_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del language_db
    rc, out, err = _run(["route", "hola", "--lang", "xx"], capsys)
    assert rc == 0, err
    payload = json.loads(out)
    assert payload["kind"] == "refuse"
    assert payload["reason"] == "unsupported_language"


def test_validate_runs(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, err = _run(["validate"], capsys)
    assert rc == 0, (out, err)


def test_audio_verify(audio_assets: Path, capsys: pytest.CaptureFixture[str]) -> None:
    del audio_assets
    rc, out, err = _run(["audio", "verify"], capsys)
    assert rc == 0, err
    assert "verified" in out


def test_unknown_command_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["nonsense"])
    assert excinfo.value.code == 2
