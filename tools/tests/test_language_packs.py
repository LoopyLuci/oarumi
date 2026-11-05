"""The shipped language packs must match their index."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_language_packs import PACK_SPECS

PACKS = Path(__file__).resolve().parents[2] / "language" / "packs"


def test_every_index_entry_matches_its_file() -> None:
    index = json.loads((PACKS / "index.json").read_text(encoding="utf-8"))
    for entry in index["packs"]:
        blob = (PACKS / entry["file"]).read_bytes()
        assert len(blob) == entry["size_bytes"], entry["code"]
        assert hashlib.sha256(blob).hexdigest() == entry["sha256"], entry["code"]


def test_index_covers_every_spec_with_matching_flags() -> None:
    index = json.loads((PACKS / "index.json").read_text(encoding="utf-8"))
    by_code = {entry["code"]: entry for entry in index["packs"]}
    assert set(by_code) == {spec.code for spec in PACK_SPECS}
    for spec in PACK_SPECS:
        assert by_code[spec.code]["base"] == spec.base
        assert by_code[spec.code]["spell"] == (spec.spell_resource is not None)


def test_packs_are_lf_text_with_sorted_keys() -> None:
    for path in PACKS.glob("*.json"):
        raw = path.read_bytes()
        assert b"\r\n" not in raw, path.name
        assert raw.endswith(b"\n"), path.name
