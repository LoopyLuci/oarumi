"""Benchmarks. Run with `pytest tests/bench --benchmark-only`.

The nightly CI job compares results against tests/bench/baseline.json with a
20% tolerance (see tools/bench_compare.py).
"""

from __future__ import annotations

import pytest
from oarumi.types import TranslationRequest


@pytest.mark.benchmark(group="pipeline")
def test_translate_phrasebook_hit(benchmark, bench_pipeline) -> None:
    req = TranslationRequest(text="hola", lang="es", modality="spoken")
    result = benchmark(bench_pipeline.translate, req)
    assert result.surface.phonemes


@pytest.mark.benchmark(group="pipeline")
def test_translate_signed_modality(benchmark, bench_pipeline) -> None:
    req = TranslationRequest(text="hola", lang="es", modality="signed")
    result = benchmark(bench_pipeline.translate, req)
    assert result.modalities.get("signed")


@pytest.mark.benchmark(group="pipeline")
def test_translate_tactile_modality(benchmark, bench_pipeline) -> None:
    req = TranslationRequest(text="hola", lang="es", modality="tactile")
    result = benchmark(bench_pipeline.translate, req)
    assert result.modalities.get("tactile")


@pytest.mark.benchmark(group="pipeline")
def test_translate_degraded_path(benchmark, bench_pipeline) -> None:
    req = TranslationRequest(text="hola", lang="xx", modality="spoken")
    result = benchmark(bench_pipeline.translate, req)
    assert result.degraded


@pytest.mark.benchmark(group="nsm")
def test_decompose_tier_a(benchmark, bench_db) -> None:
    from oarumi.nsm.decomposer import NSMDecomposerTierA

    dec = NSMDecomposerTierA(bench_db)
    nsm = benchmark(dec.decompose, "I want water")
    assert nsm.valid


@pytest.mark.benchmark(group="nsm")
def test_realize(benchmark, bench_db) -> None:
    from oarumi.nsm.decomposer import NSMDecomposerTierA
    from oarumi.nsm.realizer import NSMRealizer

    dec = NSMDecomposerTierA(bench_db)
    rea = NSMRealizer(bench_db)
    nsm = dec.decompose("I want water")
    surface = benchmark(rea.realize, nsm)
    assert surface.phonemes


@pytest.mark.benchmark(group="reliability")
def test_shield_valid_path(benchmark, tmp_path) -> None:
    from oarumi.reliability.audit_log import AuditLog
    from oarumi.reliability.symbolic_shield import ParityContract, SymbolicShield
    from oarumi.types import ValidationOutcome

    shield = SymbolicShield(audit=AuditLog(tmp_path / "audit.jsonl"))
    call = shield.wrap(
        component="x",
        neural=lambda _: "ok",
        validator=lambda _: ValidationOutcome(valid=True),
        fallback=lambda _: "fb",
        contract=ParityContract(validity_required=True, latency_ceiling_ms=1000),
    )
    r = benchmark(call, 1)
    assert r.decision == "use_neural"


@pytest.mark.benchmark(group="reliability")
def test_shield_fallback_path(benchmark, tmp_path) -> None:
    from oarumi.reliability.audit_log import AuditLog
    from oarumi.reliability.symbolic_shield import ParityContract, SymbolicShield
    from oarumi.types import ValidationOutcome

    shield = SymbolicShield(audit=AuditLog(tmp_path / "audit.jsonl"))
    call = shield.wrap(
        component="x",
        neural=lambda _: "bad",
        validator=lambda _: ValidationOutcome(valid=False, errors=("bad",)),
        fallback=lambda _: "fb",
        contract=ParityContract(validity_required=True, latency_ceiling_ms=1000),
    )
    r = benchmark(call, 1)
    assert r.decision == "use_fallback"
