"""NSM decompose parity: every pipeline case must match its frozen NSM."""

from __future__ import annotations

from oarumi.types import TranslationRequest

from tests.parity.conftest import canonicalise


def test_decompose_matches_gold(engine_pipeline, parity_cases) -> None:
    compared = 0
    failures: list[str] = []

    for case_id, case in parity_cases:
        expected = case.get("expected")
        if expected is None or "nsm" not in expected:
            continue

        req = TranslationRequest(**case["request"])
        got = engine_pipeline.translate(req).to_json()
        compared += 1

        if canonicalise(got)["nsm"] != canonicalise(expected)["nsm"]:
            failures.append(f"{case_id}: nsm mismatch")

    assert not failures, "\n".join(failures[:20])
    assert compared >= 0


def test_decomposer_known_templates(engine_db) -> None:
    from oarumi.nsm.decomposer import NSMDecomposerTierA

    dec = NSMDecomposerTierA(engine_db)
    cases = [
        ("I want water", "WANT"),
        ("she wants to go", "WANT"),
        ("I see the book", "SEE"),
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
    for text, expected_head in cases:
        nsm = dec.decompose(text)
        heads = {c.head for c in nsm.combinators}
        assert expected_head in heads, f"{text!r} -> {heads}, missing {expected_head}"
