"""Run the parity corpus through the Python pipeline. Emit machine-readable JSON.

Called by:
  - Batch 14 (`tools.parity_web.runner`) to feed the web GUI
  - CI (`scripts/parity_check.sh`)

Contract (per case):

    {
      "case_id":   "<filename stem>",
      "request":   {...C3 request...},
      "expected":  {...gold C3 result...} | null,
      "got":       {...C3 result...} | null,
      "match":     true | false | null,
      "error":     "<string>" | null
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PARITY_DATA = ROOT / "tests" / "parity" / "data"


def run(
    corpus: str, *, db_path: Path | None = None, target: str = "python", strict: bool = False
) -> dict[str, Any]:
    from oarumi.config import EngineConfig
    from oarumi.db import LanguageDb
    from oarumi.types import TranslationRequest

    from tools.parity_setup import build_pipeline

    cfg = EngineConfig.from_env()
    db = LanguageDb(db_path or cfg.db_path)
    pipeline = build_pipeline(db, ROOT)

    corpus_dir = PARITY_DATA / corpus
    if not corpus_dir.exists():
        return {
            "corpus": corpus,
            "target": target,
            "error": f"corpus not found: {corpus_dir}",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "cases": [],
            "started_at": _now(),
            "finished_at": _now(),
        }

    started = _now()
    cases: list[dict[str, Any]] = []
    passed = failed = 0

    try:
        for case_path in sorted(corpus_dir.glob("*.json")):
            case_id = case_path.stem
            entry: dict[str, Any] = {
                "case_id": case_id,
                "request": None,
                "expected": None,
                "got": None,
                "match": None,
                "error": None,
            }
            try:
                case = json.loads(case_path.read_text(encoding="utf-8"))
                entry["request"] = case["request"]
                entry["expected"] = case.get("expected")
                req = TranslationRequest(**case["request"])
                entry["got"] = pipeline.translate(req).to_json()
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
                failed += 1
                cases.append(entry)
                continue

            if entry["expected"] is not None:
                entry["match"] = _canonical(entry["got"]) == _canonical(entry["expected"])
                if entry["match"]:
                    passed += 1
                else:
                    failed += 1
            else:
                # No gold frozen for this case; treat as "not compared" (pass with note).
                entry["match"] = None
                if strict:
                    entry["error"] = "missing_gold"
                    failed += 1
                else:
                    passed += 1
            cases.append(entry)
    finally:
        db.close()

    return {
        "corpus": corpus,
        "target": target,
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "cases": cases,
        "started_at": started,
        "finished_at": _now(),
    }


def _canonical(out: dict[str, Any]) -> dict[str, Any]:
    """Strip machine-local fields and fold platform backend names before comparing to gold."""
    out = json.loads(json.dumps(out))  # defensive deep copy
    out.pop("request_id", None)
    for ev in out.get("failover_events", []):
        ev.pop("t", None)
    for payload in out.get("modalities", {}).values():
        payload.pop("audio_path", None)
        payload.pop("duration_ms", None)
        if payload.get("backend") in {"espeak", "android", "native"}:
            payload["backend"] = "native"
    return out


def _now() -> str:
    return datetime.now(UTC).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="parity-basic")
    parser.add_argument("--db", default=None)
    parser.add_argument("--target", default="python")
    parser.add_argument(
        "--strict", action="store_true", help="Fail on cases whose expected output is missing"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON to stdout (default when --out is absent)"
    )
    parser.add_argument("--out", default=None, help="Write JSON to this path")
    args = parser.parse_args(argv)

    result = run(
        corpus=args.corpus,
        db_path=Path(args.db) if args.db else None,
        target=args.target,
        strict=args.strict,
    )

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"OK   wrote {args.out} ({result['passed']}/{result['total']} passed)")
    else:
        print(payload)

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
