"""End-to-end parity: every corpus case's result equals the frozen gold."""

from __future__ import annotations

import pytest
from oarumi.types import TranslationRequest

from tests.parity.conftest import canonicalise


def test_pipeline_parity(engine_pipeline, parity_cases, parity_strict: bool) -> None:
    if parity_cases is None or len(parity_cases) == 0:
        pytest.skip("no cases")

    compared = 0
    failures: list[str] = []

    for case_id, case in parity_cases:
        req = TranslationRequest(**case["request"])
        got = canonicalise(engine_pipeline.translate(req).to_json())

        expected = case.get("expected")
        if expected is None:
            if parity_strict:
                failures.append(f"{case_id}: missing gold (strict mode)")
            continue

        compared += 1
        want = canonicalise(expected)
        if got != want:
            diff_keys = [k for k in want if got.get(k) != want[k]]
            failures.append(f"{case_id}: diff in {diff_keys}")

    assert not failures, "parity failures:\n" + "\n".join(failures[:20])
    assert compared > 0 or not parity_strict
