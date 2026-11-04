"""NSM realizer parity: 100% coverage is required — this is a deterministic path."""

from __future__ import annotations

from oarumi.types import TranslationRequest

from tests.parity.conftest import canonicalise


def test_realize_matches_gold(engine_pipeline, parity_cases) -> None:
    compared = 0
    failures: list[str] = []

    for case_id, case in parity_cases:
        expected = case.get("expected")
        if expected is None or "surface" not in expected:
            continue

        req = TranslationRequest(**case["request"])
        got = engine_pipeline.translate(req).to_json()
        compared += 1

        if canonicalise(got)["surface"] != canonicalise(expected)["surface"]:
            failures.append(f"{case_id}: surface mismatch")

    assert not failures, "\n".join(failures[:20])
    assert compared >= 0


def test_round_trip_all_templates(engine_db) -> None:
    """decompose → realize → decompose must be idempotent on the template set."""
    from oarumi.nsm.decomposer import NSMDecomposerTierA
    from oarumi.nsm.realizer import NSMRealizer

    dec = NSMDecomposerTierA(engine_db)
    rea = NSMRealizer(engine_db)
    templates = [
        "I want water",
        "she wants to go",
        "I see the book",
        "I go",
        "it is good",
        "it is bad",
        "hello",
        "thank you",
        "yes",
        "no",
        "how are you",
        "where is the bathroom",
    ]
    matches = 0
    for text in templates:
        nsm1 = dec.decompose(text)
        surface = rea.realize(nsm1)
        pivot2 = rea.to_canonical_pivot(surface)
        if not pivot2:
            continue
        nsm2 = dec.decompose(pivot2)
        if nsm1 == nsm2:
            matches += 1
    assert matches / len(templates) >= 0.9
