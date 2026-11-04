"""Runner: python path is exercised end-to-end; kotlin path is mocked."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.parity_web.runner import Runner
from tools.parity_web.store import RunStore


@pytest.mark.asyncio()
async def test_python_runner_produces_report(tmp_path: Path) -> None:
    """Python target runs the real parity_runner against parity-basic."""
    root = Path(__file__).resolve().parents[3]
    if not (root / "tests" / "parity" / "data" / "parity-basic").exists():
        pytest.skip("parity-basic corpus missing; run tools/generate_parity_corpus.py")

    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["python"])
    runner = Runner(repo_root=root)
    await runner.run(run_id, "parity-basic", ["python"], store)

    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "done"
    payload = run["target_results"]["python"]["payload"]
    assert payload is not None
    assert payload["target"] == "python"
    assert payload["total"] > 0


@pytest.mark.asyncio()
async def test_unknown_target_records_error(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["nonexistent"])
    runner = Runner(repo_root=tmp_path)
    await runner.run(run_id, "parity-basic", ["nonexistent"], store)

    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "failed"
    assert "nonexistent" in (run["target_results"]["nonexistent"]["error"] or "")


@pytest.mark.asyncio()
async def test_kotlin_runner_handles_missing_gradlew(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["kotlin"])
    runner = Runner(repo_root=tmp_path)  # empty tmp repo → no gradlew
    await runner.run(run_id, "parity-basic", ["kotlin"], store)

    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "failed"
    assert "gradlew" in (run["target_results"]["kotlin"]["error"] or "")


def test_parse_junit_counts_pass_and_fail(tmp_path: Path) -> None:
    xml_dir = tmp_path / "results"
    xml_dir.mkdir()
    (xml_dir / "TEST-oarumi.xml").write_text(
        '<testsuite name="oarumi">'
        '<testcase name="case_a"/>'
        '<testcase name="case_b"><failure>mismatch</failure></testcase>'
        "</testsuite>",
        encoding="utf-8",
    )
    (xml_dir / "broken.xml").write_text("<not-xml", encoding="utf-8")

    payload = Runner._parse_junit(xml_dir, "parity-basic")

    assert payload["target"] == "kotlin"
    assert payload["total"] == 2
    assert payload["passed"] == 1
    assert payload["failed"] == 1
    assert {c["case_id"]: c["match"] for c in payload["cases"]} == {
        "case_a": True,
        "case_b": False,
    }
