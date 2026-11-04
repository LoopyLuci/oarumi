"""RunStore: creation, target completion, readiness, listing."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.parity_web.store import RunStore


def test_create_and_get_run(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["python", "kotlin"])
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "pending"
    assert set(run["targets"]) == {"python", "kotlin"}
    assert set(run["target_results"]) == {"python", "kotlin"}


def test_create_run_rejects_empty_targets(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    with pytest.raises(ValueError):
        store.create_run("parity-basic", [])


def test_complete_target_and_finish(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["python"])
    store.mark_running(run_id)
    store.mark_target_running(run_id, "python")
    store.complete_target(run_id, "python", payload={"total": 5})
    store.finish_run(run_id)
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "done"
    assert run["target_results"]["python"]["status"] == "done"
    assert run["target_results"]["python"]["payload"] == {"total": 5}


def test_failed_target_marks_run_failed(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["python"])
    store.complete_target(run_id, "python", error="boom")
    store.finish_run(run_id)
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "failed"
    assert "boom" in (run["error"] or "")


def test_partial_target_status(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    run_id = store.create_run("parity-basic", ["python", "kotlin"])
    store.complete_target(run_id, "python", payload={"total": 1})
    store.finish_run(run_id)
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "partial"


def test_list_runs_newest_first(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    import time

    ids = []
    for i in range(3):
        ids.append(store.create_run(f"c{i}", ["python"]))
        time.sleep(0.01)
    listed = store.list_runs()
    assert [r["id"] for r in listed] == list(reversed(ids))


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "runs.db"
    store1 = RunStore(path)
    run_id = store1.create_run("parity-basic", ["python"])
    store2 = RunStore(path)
    assert store2.get_run(run_id) is not None
