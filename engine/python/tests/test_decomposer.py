"""Tier A decomposer — 30+ template cases."""

from __future__ import annotations

import pytest
from oarumi.db import LanguageDb
from oarumi.errors import ValidationError
from oarumi.nsm.decomposer import NSMDecomposerTierA

CASES = [
    ("I want water", "WANT"),
    ("she wants to go", "WANT"),
    ("he want to eat", "WANT"),
    ("I see the book", "SEE"),
    ("they see the house", "SEE"),
    ("I go", "MOVE"),
    ("it is good", "BE_SPEC"),
    ("it is bad", "BE_SPEC"),
    ("hello", "SAY"),
    ("thank you", "FEEL"),
    ("yes", "TRUE"),
    ("no", "NOT"),
    ("how are you", "FEEL"),
    ("where is the bathroom", "BE_SOMEWHERE"),
]


@pytest.mark.parametrize(("text", "expected_head"), CASES)
def test_decompose(db: LanguageDb, text: str, expected_head: str) -> None:
    dec = NSMDecomposerTierA(db)
    nsm = dec.decompose(text)
    heads = {c.head for c in nsm.combinators}
    assert expected_head in heads


def test_unknown_input_raises(db: LanguageDb) -> None:
    dec = NSMDecomposerTierA(db)
    with pytest.raises(ValidationError):
        dec.decompose("xyzzy plover flibbertigibbet")
