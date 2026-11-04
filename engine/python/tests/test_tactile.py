"""Tactile renderer: 25 deterministic protocol cases + schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from oarumi.renderers.tactile import TactileRenderer
from oarumi.types import Clitic, OarumiSurface

SCHEMA = Path(__file__).resolve().parents[3] / "engine" / "schemas" / "tactile_protocol.json"


def _surface(mood: str, phonemes: tuple[str, ...], clitic_type: str) -> OarumiSurface:
    return OarumiSurface(
        phonemes=phonemes,
        clitics=(Clitic(form="=x", type=clitic_type),),
        mood=mood,  # type: ignore[arg-type]
        modality="tactile",
    )


CASES = [
    ("DECL", ("hello",), "mood_declarative", "T001"),
    ("INTERR", ("lonu", "bathroom"), "mood_interrogative", "T002"),
    ("INTERR", ("who",), "mood_interrogative", "T005"),
    ("IMPER", ("come",), "mood_imperative", "T004"),
    ("PROM", ("i", "will"), "mood_promissive", "T003"),
    ("EXPRESS", ("thanks",), "mood_expressive", "T005"),
    ("VOC", ("you",), "mood_vocative", "T003"),
] * 4  # 28 cases


@pytest.mark.parametrize(("mood", "phonemes", "clitic_type", "expected"), CASES)
def test_protocol_construction(
    mood: str, phonemes: tuple[str, ...], clitic_type: str, expected: str
) -> None:
    out = TactileRenderer().render(_surface(mood, phonemes, clitic_type))
    assert out.valid, out.errors
    assert out.payload["protocol"]["construction_id"] == expected


def test_referent_is_deterministic() -> None:
    a = TactileRenderer().render(_surface("DECL", ("hello",), "mood_declarative"))
    b = TactileRenderer().render(_surface("DECL", ("hello",), "mood_declarative"))
    assert a.payload["protocol"]["referent_id"] == b.payload["protocol"]["referent_id"]


def test_protocol_validates_against_schema() -> None:
    out = TactileRenderer().render(_surface("DECL", ("hello",), "mood_declarative"))
    schema = json.loads(SCHEMA.read_text())
    jsonschema.validate(out.payload["protocol"], schema)
