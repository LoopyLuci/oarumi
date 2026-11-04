"""The local CI runner: preflight checks, scheduling, cache, and reporting."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import ci


def _ok(detail: str = "") -> tuple[bool, str]:
    return True, detail


def _fail(detail: str = "boom") -> tuple[bool, str]:
    return False, detail


def _step(name: str, fn: object, needs: tuple[str, ...] = (), cacheable: bool = False) -> ci.Step:
    return ci.Step(
        name=name,
        modes=frozenset({"full"}),
        needs=needs,
        fn=fn,  # type: ignore[arg-type]
        inputs=("__none__",),
        cacheable=cacheable,
    )


@pytest.fixture()
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "state"
    monkeypatch.setattr(ci, "STATE_DIR", state)
    monkeypatch.setattr(ci, "CACHE_FILE", state / "cache.json")
    monkeypatch.setattr(ci, "REPORT_FILE", state / "report.json")
    monkeypatch.setattr(ci, "LOG_DIR", state / "logs")
    return state


def test_result_passed_only_for_ok_and_cached() -> None:
    assert ci.Result("a", "ok", 0.0).passed
    assert ci.Result("a", "cached", 0.0).passed
    assert not ci.Result("a", "fail", 0.0).passed
    assert not ci.Result("a", "skipped", 0.0).passed


def test_secret_scanner_flags_private_key_and_skips_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Assembled at runtime so this test file does not contain a real-looking secret.
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    leaky = tmp_path / "leaky.txt"
    leaky.write_text(header + "\nMIIE\n", encoding="utf-8")
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\0\0AKIA" + b"A" * 16)
    monkeypatch.setattr(ci, "_tracked_files", lambda: [leaky, binary])
    monkeypatch.setattr(ci, "ROOT", tmp_path)

    ok, detail = ci.check_secrets()
    assert ok is False
    assert "leaky.txt (private-key)" in detail
    assert "blob.bin" not in detail


def test_secret_scanner_passes_clean_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text("print('hello')\n", encoding="utf-8")
    monkeypatch.setattr(ci, "_tracked_files", lambda: [clean])
    monkeypatch.setattr(ci, "ROOT", tmp_path)
    assert ci.check_secrets() == (True, "no secret patterns in tracked or unignored files")


def test_index_eol_parser_reports_only_committed_crlf(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = b"i/crlf    w/crlf  attr/text=auto\tcrlf.py\0i/lf      w/lf    attr/text=auto\tlf.py\0"

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=raw, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ci._index_crlf_files() == ["crlf.py"]
    ok, detail = ci.check_line_endings()
    assert ok is False
    assert "crlf.py" in detail


def test_line_endings_fall_back_to_bytes_without_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    crlf = tmp_path / "doc.md"
    crlf.write_bytes(b"one\r\ntwo\r\n")
    monkeypatch.setattr(ci, "_index_crlf_files", lambda: None)
    monkeypatch.setattr(ci, "_tracked_files", lambda: [crlf])
    monkeypatch.setattr(ci, "ROOT", tmp_path)
    ok, _ = ci.check_line_endings()
    assert ok is False


def test_fingerprint_changes_with_content_only_for_matched_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "a.py"
    other = tmp_path / "notes.txt"
    src.write_text("x = 1\n", encoding="utf-8")
    other.write_text("first\n", encoding="utf-8")
    monkeypatch.setattr(ci, "_tracked_files", lambda: [src, other])
    monkeypatch.setattr(ci, "ROOT", tmp_path)

    before = ci.fingerprint(("*.py",), "cmd")
    other.write_text("changed\n", encoding="utf-8")
    assert ci.fingerprint(("*.py",), "cmd") == before
    src.write_text("x = 2\n", encoding="utf-8")
    assert ci.fingerprint(("*.py",), "cmd") != before
    assert ci.fingerprint(("*.py",), "other-cmd") != ci.fingerprint(("*.py",), "cmd")


def test_schedule_orders_dependencies_and_skips_dependents_of_failures(
    isolated_state: Path,
) -> None:
    calls: list[str] = []

    def recorder(name: str, ok: bool) -> object:
        def run() -> tuple[bool, str]:
            calls.append(name)
            return ok, name

        return run

    steps = [
        _step("a", recorder("a", True)),
        _step("b", recorder("b", False), needs=("a",)),
        _step("c", recorder("c", True), needs=("b",)),
        _step("d", recorder("d", True)),
    ]
    results = ci.schedule(steps, use_cache=False, jobs=3)

    assert results["a"].status == "ok"
    assert results["b"].status == "fail"
    assert results["c"].status == "skipped"
    assert "dependency failed: b" in results["c"].detail
    assert results["d"].status == "ok"
    assert calls.index("a") < calls.index("b")
    assert "c" not in calls


def test_schedule_rejects_unknown_dependency(isolated_state: Path) -> None:
    with pytest.raises(ValueError, match="unknown step 'ghost'"):
        ci.schedule([_step("a", _ok, needs=("ghost",))], use_cache=False, jobs=1)


def test_cache_serves_second_run_without_executing(isolated_state: Path) -> None:
    runs = {"n": 0}

    def counted() -> tuple[bool, str]:
        runs["n"] += 1
        return True, "done"

    step = _step("cached-step", counted, cacheable=True)
    first = ci.schedule([step], use_cache=True, jobs=1)
    second = ci.schedule([step], use_cache=True, jobs=1)

    assert first["cached-step"].status == "ok"
    assert second["cached-step"].status == "cached"
    assert runs["n"] == 1
    assert json.loads((isolated_state / "cache.json").read_text(encoding="utf-8"))


def test_failed_steps_are_never_cached(isolated_state: Path) -> None:
    runs = {"n": 0}

    def flaky() -> tuple[bool, str]:
        runs["n"] += 1
        return False, "nope"

    step = _step("flaky", flaky, cacheable=True)
    ci.schedule([step], use_cache=True, jobs=1)
    again = ci.schedule([step], use_cache=True, jobs=1)
    assert again["flaky"].status == "fail"
    assert runs["n"] == 2


def test_precondition_skips_step(isolated_state: Path) -> None:
    step = ci.Step(
        name="device",
        modes=frozenset({"all"}),
        fn=_ok,
        precondition=lambda: "no device attached",
        cacheable=False,
    )
    result = ci.run_step(step, use_cache=False, cache={})
    assert result.status == "skipped"
    assert result.detail == "no device attached"


def test_modes_select_expected_steps() -> None:
    fast = {s.name for s in ci.build_steps("fast")}
    full = {s.name for s in ci.build_steps("full")}
    everything = {s.name for s in ci.build_steps("all")}

    assert "preflight-secrets" in fast
    assert "unit" not in fast
    assert "unit" in full
    assert "android" in full
    assert "android" not in fast
    assert {"chaos", "bench", "android"} <= everything


def test_gradle_command_is_absent_without_wrapper(tmp_path: Path) -> None:
    assert ci._gradle_cmd(tmp_path) is None


def test_gradle_command_uses_wrapper_when_present(tmp_path: Path) -> None:
    name = "gradlew.bat" if os.name == "nt" else "gradlew"
    (tmp_path / name).write_text("", encoding="utf-8")
    cmd = ci._gradle_cmd(tmp_path)
    assert cmd is not None
    assert cmd[0].endswith(name)
    assert ":engine:test" in cmd


def test_write_report_summarises_results(isolated_state: Path) -> None:
    results = {
        "a": ci.Result("a", "ok", 0.5, ""),
        "b": ci.Result("b", "fail", 1.0, "boom"),
    }
    ci.write_report("full", results, 1.5)
    report = json.loads((isolated_state / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert [s["name"] for s in report["steps"]] == ["a", "b"]


def test_main_list_prints_every_step(capsys: pytest.CaptureFixture[str]) -> None:
    assert ci.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "unit" in out
    assert "android" in out


def test_main_only_runs_dependencies_too(
    isolated_state: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[str] = []

    def record(steps: list[ci.Step], use_cache: bool, jobs: int) -> dict[str, ci.Result]:
        seen.extend(s.name for s in steps)
        return {s.name: ci.Result(s.name, "ok", 0.0) for s in steps}

    monkeypatch.setattr(ci, "schedule", record)
    assert ci.main(["--mode", "full", "--only", "unit"]) == 0
    assert "unit" in seen
    assert "preflight-tools" in seen
    assert "parity-complex" not in seen


def test_main_returns_nonzero_when_a_step_fails(
    isolated_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(steps: list[ci.Step], use_cache: bool, jobs: int) -> dict[str, ci.Result]:
        return {s.name: ci.Result(s.name, "fail", 0.0, "bad") for s in steps}

    monkeypatch.setattr(ci, "schedule", failing)
    assert ci.main(["--mode", "fast"]) == 1


def test_install_hooks_points_git_at_scripts_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ci.install_hooks() == 0
    assert calls == [["git", "config", "core.hooksPath", "scripts/hooks"]]


def test_android_step_skips_without_wrapper_or_jdk(monkeypatch: pytest.MonkeyPatch) -> None:
    assert ci._android_missing(None) == "android/gradlew not found"
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert "no JDK" in str(ci._android_missing(["gradlew"]))
    monkeypatch.setenv("JAVA_HOME", "/opt/jdk")
    assert ci._android_missing(["gradlew"]) is None
