"""Local CI/CD runner for Oarumi. Runs the same gates on Windows, macOS and Linux.

    python -m tools.ci --mode fast      # pre-commit: preflight, lint, schemas
    python -m tools.ci --mode full      # pre-push: everything except device/nightly jobs
    python -m tools.ci --mode all       # nightly: adds chaos, bench, Android build
    python -m tools.ci --list           # show steps and their modes
    python -m tools.ci --install-hooks  # point git at scripts/hooks

Steps are scheduled as a dependency graph and run in parallel. A step whose
input files, command and interpreter are unchanged since its last pass is
served from the cache (.oarumi/ci/cache.json). Every run writes a JSON report
to .oarumi/ci/report.json and a per-step log to .oarumi/ci/logs/.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".oarumi" / "ci"
CACHE_FILE = STATE_DIR / "cache.json"
REPORT_FILE = STATE_DIR / "report.json"
LOG_DIR = STATE_DIR / "logs"
HOOKS_DIR = "scripts/hooks"

MODES = ("fast", "full", "all")
MAX_FILE_BYTES = 5 * 1024 * 1024
COVERAGE_FLOOR = 85
PY_INPUTS = ["*.py", "pyproject.toml"]
SCHEMA_INPUTS = ["language/*", "language/**/*", "tools/*.py", "*.json"]

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "private-key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----"
    ),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
}


@dataclass(frozen=True)
class Result:
    name: str
    status: str  # ok | fail | cached | skipped
    seconds: float
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.status in {"ok", "cached"}


@dataclass
class Step:
    name: str
    modes: frozenset[str]
    needs: tuple[str, ...] = ()
    cmd: list[str] | None = None
    fn: Callable[[], tuple[bool, str]] | None = None
    env: dict[str, str] = field(default_factory=dict)
    inputs: tuple[str, ...] = tuple(PY_INPUTS)
    cacheable: bool = True
    precondition: Callable[[], str | None] | None = None
    cwd: Path | None = None


def _py(*args: str) -> list[str]:
    return [sys.executable, *args]


def _tracked_files() -> list[Path]:
    """Files git knows about plus untracked files that are not ignored."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".venv" not in p.parts]
    return [ROOT / rel for rel in out.decode("utf-8").split("\0") if rel]


def _rel(path: Path) -> str:
    """Repo-relative path for messages; absolute when the path lives outside the repo."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _is_text(data: bytes) -> bool:
    return b"\0" not in data[:8000]


# --- preflight checks ---------------------------------------------------


def check_python_version() -> tuple[bool, str]:
    ok = sys.version_info >= (3, 11)
    return ok, f"python {sys.version.split()[0]} (need >= 3.11)"


def check_tools() -> tuple[bool, str]:
    missing = []
    for module in ("ruff", "black", "mypy", "pytest", "yaml"):
        probe = subprocess.run(_py("-c", f"import {module}"), capture_output=True, cwd=ROOT)
        if probe.returncode != 0:
            missing.append(module)
    if missing:
        return (
            False,
            f"missing Python modules: {', '.join(missing)} (run: pip install -e \".[dev]\")",
        )
    return True, "ruff, black, mypy, pytest and PyYAML importable"


def check_secrets() -> tuple[bool, str]:
    hits: list[str] = []
    for path in _tracked_files():
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        data = path.read_bytes()
        if not _is_text(data):
            continue
        text = data.decode("utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT).as_posix()} ({label})")
    if hits:
        return False, "possible secrets: " + "; ".join(hits)
    return True, "no secret patterns in tracked or unignored files"


def check_file_sizes() -> tuple[bool, str]:
    big = [
        f"{p.relative_to(ROOT).as_posix()} ({p.stat().st_size // 1024} KiB)"
        for p in _tracked_files()
        if p.is_file() and p.stat().st_size > MAX_FILE_BYTES
    ]
    if big:
        return False, f"files over {MAX_FILE_BYTES // 1024 // 1024} MiB: " + "; ".join(big)
    return True, f"no tracked file over {MAX_FILE_BYTES // 1024 // 1024} MiB"


def check_workflows() -> tuple[bool, str]:
    import yaml

    bad = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            bad.append(f"{path.name}: {exc}")
    if bad:
        return False, "invalid workflow YAML: " + "; ".join(bad)
    return True, "workflow YAML parses"


def _index_crlf_files() -> list[str] | None:
    """Tracked files whose committed (index) content has CRLF; None if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--eol", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    offenders = []
    for record in out.decode("utf-8").split("\0"):
        if not record:
            continue
        # Each record is "<i/eol> <w/eol> <attr> <TAB> <path>".
        fields, _, rel = record.partition("\t")
        if fields.split()[0] == "i/crlf":
            offenders.append(rel)
    return offenders


def check_line_endings() -> tuple[bool, str]:
    # Judge what gets committed (the index), not this machine's checkout.
    offenders = _index_crlf_files()
    if offenders is None:
        offenders = [
            p.relative_to(ROOT).as_posix()
            for p in _tracked_files()
            if p.is_file()
            and p.suffix in {".py", ".md", ".yml", ".yaml", ".sh", ".toml", ".json"}
            and b"\r\n" in p.read_bytes()
        ]
    if offenders:
        return False, f"CRLF committed in {len(offenders)} file(s), first: {offenders[0]}"
    return True, "LF line endings in committed text files"


# --- fingerprints and cache ---------------------------------------------


def fingerprint(patterns: tuple[str, ...], extra: str) -> str:
    digest = hashlib.sha256(extra.encode("utf-8"))
    for path in sorted(_tracked_files()):
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            continue
        if any(fnmatch.fnmatch(rel, pat) for pat in patterns):
            digest.update(rel.encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _load_cache() -> dict[str, str]:
    try:
        data: dict[str, str] = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _step_key(step: Step) -> str:
    cmd = " ".join(step.cmd or [step.name])
    extra = f"{cmd}|{sys.version}|{sorted(step.env.items())}"
    return fingerprint(step.inputs, extra)


# --- execution ----------------------------------------------------------


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    scripts = Path(sys.executable).parent
    env["PATH"] = os.pathsep.join([str(scripts), env.get("PATH", "")])
    return env


def _run_cmd(step: Step) -> tuple[bool, str]:
    assert step.cmd is not None
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{step.name}.log"
    env = _env()
    env.update(step.env)
    proc = subprocess.run(
        step.cmd,
        cwd=step.cwd or ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode == 0:
        return True, f"log: {_rel(log)}"
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-12:])
    return False, f"exit {proc.returncode}; log: {_rel(log)}\n{tail}"


def run_step(step: Step, use_cache: bool, cache: dict[str, str]) -> Result:
    started = time.monotonic()

    def elapsed() -> float:
        return time.monotonic() - started

    if step.precondition is not None:
        reason = step.precondition()
        if reason is not None:
            return Result(step.name, "skipped", elapsed(), reason)

    key = _step_key(step) if step.cacheable else ""
    if use_cache and step.cacheable and cache.get(step.name) == key:
        return Result(step.name, "cached", elapsed(), "inputs unchanged since last pass")

    if step.fn is not None:
        ok, detail = step.fn()
    else:
        ok, detail = _run_cmd(step)

    if ok and step.cacheable:
        cache[step.name] = key
    return Result(step.name, "ok" if ok else "fail", elapsed(), detail)


def schedule(steps: list[Step], use_cache: bool, jobs: int) -> dict[str, Result]:
    """Run steps in dependency order, parallel where independent.

    A step whose dependency failed or was skipped is itself skipped.
    """
    cache = _load_cache() if use_cache else {}
    known = {s.name for s in steps}
    for step in steps:
        missing = [d for d in step.needs if d not in known]
        if missing:
            raise ValueError(f"step {step.name!r} needs unknown step {missing[0]!r}")

    done: dict[str, Result] = {}
    pending: dict[str, Step] = {s.name: s for s in steps}
    running: dict[str, cf.Future[Result]] = {}

    with cf.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        while pending or running:
            for step in list(pending.values()):
                blockers = [d for d in step.needs if d in done and not done[d].passed]
                if blockers:
                    done[step.name] = Result(
                        step.name, "skipped", 0.0, f"dependency failed: {blockers[0]}"
                    )
                    del pending[step.name]
            for step in list(pending.values()):
                if all(d in done for d in step.needs):
                    running[step.name] = pool.submit(run_step, step, use_cache, cache)
                    del pending[step.name]
            if not running:
                if pending:
                    raise RuntimeError(f"unschedulable steps: {sorted(pending)}")
                break
            finished, _ = cf.wait(list(running.values()), return_when=cf.FIRST_COMPLETED)
            for name, future in list(running.items()):
                if future in finished:
                    done[name] = future.result()
                    del running[name]

    if use_cache:
        _save_cache(cache)
    return done


def build_steps(mode: str, android_dir: Path | None = None) -> list[Step]:
    """Return every step whose modes include the requested mode."""
    everything = _catalogue(android_dir)
    return [s for s in everything if mode in s.modes]


def _catalogue(android_dir: Path | None) -> list[Step]:
    fast = frozenset({"fast", "full", "all"})
    full = frozenset({"full", "all"})
    everything = frozenset({"all"})
    cov = f"--cov-fail-under={COVERAGE_FLOOR}"
    gradle = _gradle_cmd(android_dir)
    return [
        Step("preflight-python", fast, fn=check_python_version, cacheable=False),
        Step("preflight-tools", fast, fn=check_tools, cacheable=False),
        Step("preflight-secrets", fast, fn=check_secrets, cacheable=False),
        Step("preflight-sizes", fast, fn=check_file_sizes, cacheable=False),
        Step("preflight-line-endings", fast, fn=check_line_endings, cacheable=False),
        Step("preflight-workflows", fast, fn=check_workflows, inputs=(".github/workflows/*",)),
        Step("ruff", fast, needs=("preflight-tools",), cmd=_py("-m", "ruff", "check", ".")),
        Step("black", fast, needs=("preflight-tools",), cmd=_py("-m", "black", "--check", ".")),
        Step(
            "schemas",
            fast,
            needs=("preflight-tools",),
            cmd=_py("tools/validate_schemas.py", "--all"),
            inputs=tuple(SCHEMA_INPUTS),
        ),
        Step(
            "mypy",
            full,
            needs=("preflight-tools",),
            cmd=_py("-m", "mypy", "--strict", "engine/python", "desktop", "tools"),
        ),
        Step(
            "primes",
            full,
            needs=("preflight-tools",),
            cmd=_py("tools/validate_primes.py"),
            inputs=tuple(SCHEMA_INPUTS),
        ),
        Step(
            "schema-drift",
            full,
            needs=("preflight-tools",),
            cmd=_py("tools/schema_export.py", "--check"),
            inputs=tuple(SCHEMA_INPUTS),
        ),
        Step(
            "unit",
            full,
            needs=("preflight-tools", "ruff"),
            cmd=_py(
                "-m",
                "pytest",
                "engine/python/tests",
                "desktop/tests",
                "tools/tests",
                "tools/parity_web/tests",
                "-q",
                "--cov=oarumi",
                "--cov=desktop",
                "--cov=tools",
                cov,
                "-p",
                "no:cacheprovider",
            ),
        ),
        Step(
            "parity-basic-strict",
            full,
            needs=("preflight-tools",),
            cmd=_py(
                "-m",
                "pytest",
                "tests/parity",
                "-q",
                "--parity-corpus=parity-basic",
                "-p",
                "no:cacheprovider",
            ),
            env={"OARUMI_STRICT_PARITY": "1"},
            inputs=("*.py", "tests/parity/data/parity-basic/*", "language/*"),
        ),
        Step(
            "parity-complex",
            full,
            needs=("preflight-tools",),
            cmd=_py(
                "-m",
                "pytest",
                "tests/parity",
                "-q",
                "--parity-corpus=parity-complex",
                "-p",
                "no:cacheprovider",
            ),
            inputs=("*.py", "tests/parity/data/parity-complex/*", "language/*"),
        ),
        Step(
            "fault",
            full,
            needs=("preflight-tools",),
            cmd=_py("-m", "pytest", "tests/fault", "-q", "-p", "no:cacheprovider"),
        ),
        Step(
            "offline",
            full,
            needs=("preflight-tools",),
            cmd=_py("-m", "pytest", "tests/offline", "-q", "-p", "no:cacheprovider"),
        ),
        Step(
            "docs-links",
            full,
            needs=("preflight-tools",),
            cmd=_py(
                "-m", "pytest", "tools/tests/test_docs_links.py", "-q", "-p", "no:cacheprovider"
            ),
            inputs=("*.md",),
        ),
        Step(
            "chaos",
            everything,
            needs=("preflight-tools",),
            cmd=_py("-m", "pytest", "tests/chaos", "-q", "--timeout=300", "-p", "no:cacheprovider"),
        ),
        Step(
            "bench",
            everything,
            needs=("preflight-tools",),
            cmd=_py(
                "-m",
                "pytest",
                "tests/bench",
                "-q",
                "--benchmark-only",
                f"--benchmark-json={(STATE_DIR / 'bench.json').as_posix()}",
                "-p",
                "no:cacheprovider",
            ),
            cacheable=False,
        ),
        Step(
            "bench-compare",
            everything,
            needs=("bench",),
            cmd=_py(
                "tools/bench_compare.py",
                "--current",
                (STATE_DIR / "bench.json").as_posix(),
                "--baseline",
                "tests/bench/baseline.json",
                "--tolerance",
                "1.20",
            ),
            cacheable=False,
        ),
        Step(
            "android",
            full,
            needs=("preflight-tools",),
            cmd=gradle,
            cwd=android_dir or ROOT / "android",
            precondition=lambda: _android_missing(gradle),
            cacheable=False,
        ),
    ]


def _android_missing(gradle: list[str] | None) -> str | None:
    """Return why the Android step cannot run here, or None when it can."""
    if gradle is None:
        return "android/gradlew not found"
    if not os.environ.get("JAVA_HOME") and shutil.which("java") is None:
        return "no JDK found (set JAVA_HOME); the android CI job still runs it"
    return None


def _gradle_cmd(android_dir: Path | None) -> list[str] | None:
    base = android_dir or ROOT / "android"
    wrapper = base / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not wrapper.exists():
        return None
    return [
        str(wrapper),
        "--quiet",
        "ktlintCheck",
        ":engine:test",
        ":app:testMlkitDebugUnitTest",
        ":app:testArgosDebugUnitTest",
    ]


# --- reporting and hooks -------------------------------------------------


def write_report(mode: str, results: dict[str, Result], wall: float) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "mode": mode,
        "wall_seconds": round(wall, 2),
        "passed": all(r.passed or r.status == "skipped" for r in results.values()),
        "steps": [
            {"name": r.name, "status": r.status, "seconds": round(r.seconds, 2), "detail": r.detail}
            for r in sorted(results.values(), key=lambda r: r.name)
        ],
    }
    REPORT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_summary(results: dict[str, Result]) -> None:
    width = max((len(r.name) for r in results.values()), default=10)
    for result in sorted(results.values(), key=lambda r: r.name):
        mark = {"ok": "PASS", "cached": "CACHE", "skipped": "SKIP", "fail": "FAIL"}[result.status]
        print(
            f"{mark:<5}  {result.name:<{width}}  {result.seconds:7.2f}s  {result.detail.splitlines()[0] if result.detail else ''}"
        )
        if result.status == "fail" and "\n" in result.detail:
            print("\n".join("      " + line for line in result.detail.splitlines()[1:]))


def install_hooks() -> int:
    subprocess.run(["git", "config", "core.hooksPath", HOOKS_DIR], cwd=ROOT, check=True)
    print(f"OK   git hooks now read from {HOOKS_DIR} (pre-commit: fast, pre-push: full)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=MODES, default="full")
    parser.add_argument(
        "--only", nargs="+", default=None, help="run only these steps (dependencies included)"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="ignore the cache and rerun everything"
    )
    parser.add_argument("--jobs", type=int, default=max(2, (os.cpu_count() or 2) // 2))
    parser.add_argument("--list", action="store_true", help="list steps and exit")
    parser.add_argument(
        "--install-hooks", action="store_true", help="configure git to use scripts/hooks"
    )
    args = parser.parse_args(argv)

    if args.install_hooks:
        return install_hooks()
    if args.list:
        for step in _catalogue(None):
            print(
                f"{step.name:<24} {','.join(sorted(step.modes)):<22} needs={','.join(step.needs) or '-'}"
            )
        return 0

    steps = build_steps(args.mode)
    if args.only:
        wanted = set(args.only)
        by_name = {s.name: s for s in steps}
        closure: set[str] = set()
        stack = [n for n in wanted if n in by_name]
        while stack:
            name = stack.pop()
            if name in closure:
                continue
            closure.add(name)
            stack.extend(d for d in by_name[name].needs if d in by_name)
        steps = [s for s in steps if s.name in closure]

    print(f"[ci] mode={args.mode} steps={len(steps)} jobs={args.jobs}")
    started = time.monotonic()
    results = schedule(steps, use_cache=not args.no_cache, jobs=args.jobs)
    wall = time.monotonic() - started
    write_report(args.mode, results, wall)
    print_summary(results)
    failed = [r.name for r in results.values() if r.status == "fail"]
    print(
        f"[ci] {'PASSED' if not failed else 'FAILED'} in {wall:.1f}s (report: {_rel(REPORT_FILE)})"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
