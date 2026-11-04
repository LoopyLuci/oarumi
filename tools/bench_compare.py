"""Compare pytest-benchmark output against a baseline JSON file.

    python tools/bench_compare.py --current bench-report.json \
      --baseline tests/bench/baseline.json --tolerance 1.20

Exits non-zero if any benchmark's mean exceeds baseline * tolerance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_current(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for bench in data.get("benchmarks", []):
        name = bench["name"].rsplit("::", 1)[-1]
        mean_s = bench["stats"]["mean"]
        out[name] = mean_s * 1000.0
    return out


def _load_baseline(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {b["name"]: float(b["mean_ms"]) for b in data.get("benchmarks", [])}


def compare(current_path: Path, baseline_path: Path, tolerance: float) -> int:
    current = _load_current(current_path)
    baseline = _load_baseline(baseline_path)

    if not baseline:
        print("WARN baseline empty; skipping comparison", file=sys.stderr)
        return 0

    regressions: list[str] = []
    missing_baseline: list[str] = []
    missing_current: list[str] = []

    for name, base in baseline.items():
        if name not in current:
            missing_current.append(name)
            continue
        cur = current[name]
        limit = base * tolerance
        if cur > limit:
            regressions.append(
                f"{name}: current={cur:.2f}ms baseline={base:.2f}ms "
                f"limit={limit:.2f}ms (ratio={cur / base:.2f}×)"
            )

    for name in current:
        if name not in baseline:
            missing_baseline.append(name)

    for name in missing_current:
        print(f"MISSING current: {name}", file=sys.stderr)
    for name in missing_baseline:
        print(f"NOTE new benchmark: {name} (add to baseline after review)")

    if regressions:
        for r in regressions:
            print(f"REGRESSION {r}", file=sys.stderr)
        return 1

    print(f"OK   {len(baseline)} benchmarks within {tolerance:.0%} tolerance")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--tolerance", type=float, default=1.20)
    args = parser.parse_args(argv)
    return compare(args.current, args.baseline, args.tolerance)


if __name__ == "__main__":
    raise SystemExit(main())
