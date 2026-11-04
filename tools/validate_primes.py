"""Validate the NSM prime inventory: IDs, uniqueness, required forms, count."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PRIMES = ROOT / "language" / "primes.yaml"

ID_RE = re.compile(r"^[A-Z][A-Z_]*$")
EXPECTED_RANGE = (60, 70)  # version-dependent; see primes.yaml header


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-count",
        type=int,
        default=None,
        help="fail unless the inventory has exactly this many primes",
    )
    args = parser.parse_args(argv)

    with PRIMES.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    errors: list[str] = []
    primes = data.get("primes", [])
    seen: dict[str, int] = {}

    for i, p in enumerate(primes):
        pid = p.get("id", "")
        if not ID_RE.match(pid):
            errors.append(f"prime[{i}] id {pid!r} is not UPPER_SNAKE")
        if pid in seen:
            errors.append(f"duplicate prime id {pid!r} at index {i} (first at {seen[pid]})")
        seen[pid] = i
        for field in ("gloss", "category", "combinators"):
            if not p.get(field):
                errors.append(f"prime {pid!r} missing field {field!r}")
        if not isinstance(p.get("combinators", []), list):
            errors.append(f"prime {pid!r} combinators must be a list")

    lo, hi = EXPECTED_RANGE
    if not (lo <= len(primes) <= hi):
        errors.append(f"prime count {len(primes)} outside expected range {lo}–{hi}")

    if args.strict_count is not None and len(primes) != args.strict_count:
        errors.append(f"prime count {len(primes)} != --strict-count {args.strict_count}")

    if data.get("needs_linguist_signoff"):
        print("NOTE inventory is flagged needs_linguist_signoff (TODO FOUND-001)")

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        return 1

    print(f"OK   {len(primes)} primes; all IDs unique; required fields present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
