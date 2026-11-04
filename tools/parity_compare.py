"""Cross-platform parity comparator.

Reads two or three parity_runner JSON reports (python, kotlin, android) and
produces a diff report. Any deterministic-path diff is a hard failure.

    python tools/parity_compare.py \
      --python /tmp/py.json \
      --kotlin /tmp/kt.json \
      --android /tmp/and.json \
      --out /tmp/diff.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _canonical(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    out: dict[str, Any] = json.loads(json.dumps(result))
    out.pop("request_id", None)
    for ev in out.get("failover_events", []):
        ev.pop("t", None)
    for payload in out.get("modalities", {}).values():
        payload.pop("audio_path", None)
        payload.pop("duration_ms", None)
        if payload.get("backend") in {"espeak", "android", "native"}:
            payload["backend"] = "native"
    return out


def _by_case(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if report is None:
        return {}
    return {case["case_id"]: case for case in report.get("cases", [])}


def compare(
    python: dict[str, Any] | None, kotlin: dict[str, Any] | None, android: dict[str, Any] | None
) -> dict[str, Any]:
    py = _by_case(python)
    kt = _by_case(kotlin)
    an = _by_case(android)

    all_ids = sorted(set(py) | set(kt) | set(an))
    diffs: list[dict[str, Any]] = []

    for case_id in all_ids:
        p = py.get(case_id, {}).get("got")
        k = kt.get(case_id, {}).get("got")
        a = an.get(case_id, {}).get("got")
        cp, ck, ca = _canonical(p), _canonical(k), _canonical(a)

        row: dict[str, Any] = {"case_id": case_id, "diffs": []}
        if cp is not None and ck is not None and cp != ck:
            row["diffs"].append("python_vs_kotlin")
        if cp is not None and ca is not None and cp != ca:
            row["diffs"].append("python_vs_android")
        if ck is not None and ca is not None and ck != ca:
            row["diffs"].append("kotlin_vs_android")
        if row["diffs"]:
            diffs.append(row)

    return {
        "total_cases": len(all_ids),
        "python_present": python is not None,
        "kotlin_present": kotlin is not None,
        "android_present": android is not None,
        "diffs": diffs,
        "clean": not diffs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=None)
    parser.add_argument("--kotlin", default=None)
    parser.add_argument("--android", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = compare(
        _load(Path(args.python)) if args.python else None,
        _load(Path(args.kotlin)) if args.kotlin else None,
        _load(Path(args.android)) if args.android else None,
    )

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    if args.json or not args.out:
        print(payload)

    if not report["clean"]:
        for d in report["diffs"][:10]:
            print(f"DIFF {d['case_id']}: {d['diffs']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
