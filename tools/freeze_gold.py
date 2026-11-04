"""Freeze deterministic pipeline outputs as parity gold. High-risk: review diffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PARITY_DATA = ROOT / "tests" / "parity" / "data"


def _hash(obj: dict[str, object]) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "language" / "oarumi.db"))
    parser.add_argument("--corpus", default="parity-basic")
    parser.add_argument(
        "--component",
        default="pipeline",
        help="pipeline | pivot | nsm_decompose | nsm_realize | tts | sign | tactile",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.component != "pipeline":
        return _freeze_component(args.component, args.corpus, Path(args.db), args.dry_run)

    return _freeze_pipeline(args.corpus, Path(args.db), args.dry_run)


def _freeze_pipeline(corpus: str, db_path: Path, dry_run: bool) -> int:
    from oarumi.db import LanguageDb
    from oarumi.types import TranslationRequest

    from tools.parity_setup import build_pipeline

    corpus_dir = PARITY_DATA / corpus
    if not corpus_dir.exists():
        print(f"FAIL corpus not found: {corpus_dir}", file=sys.stderr)
        return 2

    db = LanguageDb(db_path)
    pipeline = build_pipeline(db, ROOT)
    conn = sqlite3.connect(db_path)
    written = 0
    try:
        for case_path in sorted(corpus_dir.glob("*.json")):
            case = json.loads(case_path.read_text(encoding="utf-8"))
            req = TranslationRequest(**case["request"])
            result = pipeline.translate(req).to_json()
            result = _canonical(result)
            h = _hash(case["request"])
            if not dry_run:
                conn.execute(
                    """INSERT OR REPLACE INTO parity_gold
                         (component, input_hash, output_json, frozen_at)
                       VALUES (?, ?, ?, ?)""",
                    ("pipeline", h, json.dumps(result), datetime.now(UTC).isoformat()),
                )
                case["expected"] = result
                case_path.write_text(
                    json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
            written += 1
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
        db.close()

    mode = "DRY" if dry_run else "OK "
    print(f"{mode}  froze {written} pipeline gold output(s) for {corpus}")
    return 0


def _freeze_component(component: str, corpus: str, db_path: Path, dry_run: bool) -> int:
    """Delegate to tools.freeze_renderer_gold for tts/sign/tactile."""
    if component in {"tts", "sign", "tactile"}:
        from tools.freeze_renderer_gold import freeze_sign, freeze_tactile, freeze_tts

        fn = {"tts": freeze_tts, "sign": freeze_sign, "tactile": freeze_tactile}[component]
        n = fn()
        print(f"OK   froze {component} gold ({n} cases)")
        return 0
    print(f"FAIL unknown component: {component}", file=sys.stderr)
    return 2


def _canonical(result: dict[str, Any]) -> dict[str, Any]:
    """Strip fields that vary across runs and across platforms (mirrors parity_runner)."""
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


if __name__ == "__main__":
    raise SystemExit(main())
