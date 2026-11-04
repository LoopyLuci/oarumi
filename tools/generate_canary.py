"""Generate per-component canary fixtures used by RecoveryFSM before promoting
a neural path. Each canary is a frozen input/expected pair, selected from the
parity-basic corpus at random with a fixed seed.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tests" / "parity" / "data" / "parity-basic"
DST = ROOT / "tests" / "parity" / "data" / "canary"

COMPONENTS = {
    "pivot": 3,  # 3 canary cases per component
    "nsm_decompose": 3,
    "nsm_realize": 3,
}


def main() -> int:
    rng = random.Random(20260101)
    cases = sorted(SRC.glob("*.json"))
    if not cases:
        print("WARN no parity-basic cases; run tools/generate_parity_corpus.py first")
        return 0

    for component, n in COMPONENTS.items():
        out_dir = DST / component
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, case_path in enumerate(rng.sample(cases, min(n, len(cases))), start=1):
            data = json.loads(case_path.read_text(encoding="utf-8"))
            canary = {
                "input": data["request"],
                "expected": data.get("expected", {}),
            }
            (out_dir / f"canary_{i:02d}.json").write_text(
                json.dumps(canary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    print(f"OK   wrote canaries to {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
