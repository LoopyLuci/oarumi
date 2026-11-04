"""Fetch or generate dev-time model stubs.

Stubs are deliberately tiny (~hundreds of bytes) JSON payloads that stand in
for real model weights. They make the app importable and testable offline.

Manifest: models/dev-stubs.manifest.json
Output:   models/dev-stubs/

Usage:
    python tools/fetch_dev_stubs.py --dest models/dev-stubs
    python tools/fetch_dev_stubs.py --regenerate-hashes
    python tools/fetch_dev_stubs.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "models" / "dev-stubs.manifest.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _content_bytes(entry: dict[str, Any]) -> bytes:
    if "content" in entry:
        c = entry["content"]
        return c.encode("utf-8") if isinstance(c, str) else bytes(c)
    return b""


def _download(url: str, target: Path, timeout_s: float = 30.0) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".partial")
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        tmp.write_bytes(response.read())
    tmp.replace(target)


def fetch(
    manifest_path: Path, dest: Path, *, verify_only: bool = False, offline: bool = False
) -> int:
    if not manifest_path.exists():
        print(f"WARN manifest missing: {manifest_path}", file=sys.stderr)
        return 0  # non-fatal

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dest.mkdir(parents=True, exist_ok=True)
    failures = 0

    for entry in manifest.get("stubs", []):
        target = dest / str(entry["filename"])
        expected = str(entry["sha256"])

        if verify_only:
            if not target.exists():
                print(f"MISS {entry['filename']}", file=sys.stderr)
                failures += 1
                continue
            actual = _sha256(target.read_bytes())
            if actual != expected:
                print(f"FAIL {entry['filename']}: {actual[:8]} != {expected[:8]}", file=sys.stderr)
                failures += 1
            else:
                print(f"OK   {entry['filename']}")
            continue

        if target.exists():
            actual = _sha256(target.read_bytes())
            if actual == expected:
                print(f"SKIP {entry['filename']} (hash match)")
                continue

        try:
            if "content" in entry:
                target.write_bytes(_content_bytes(entry))
            elif "url" in entry:
                if offline:
                    print(f"WARN {entry['filename']}: offline, skipping download", file=sys.stderr)
                    continue
                _download(str(entry["url"]), target)
            else:
                print(f"WARN {entry['filename']}: no content or url", file=sys.stderr)
                continue
        except Exception as exc:
            print(f"FAIL {entry['filename']}: {exc}", file=sys.stderr)
            failures += 1
            continue

        actual = _sha256(target.read_bytes())
        if actual != expected:
            print(f"FAIL {entry['filename']}: hash mismatch after write", file=sys.stderr)
            target.unlink(missing_ok=True)
            failures += 1
        else:
            print(f"OK   {entry['filename']}")

    return 0 if failures == 0 else 1


def regenerate_hashes(manifest_path: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = 0
    for entry in manifest.get("stubs", []):
        if "content" not in entry:
            continue
        digest = _sha256(_content_bytes(entry))
        if entry.get("sha256") != digest:
            entry["sha256"] = digest
            changed += 1
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"OK   updated {changed} hash(es) in {manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dest", default=str(ROOT / "models" / "dev-stubs"))
    parser.add_argument(
        "--verify", action="store_true", help="Check hashes of already-installed stubs, no download"
    )
    parser.add_argument(
        "--regenerate-hashes",
        action="store_true",
        help="Recompute the manifest's sha256 fields from content",
    )
    parser.add_argument("--offline", action="store_true", help="Refuse any network operation")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if args.regenerate_hashes:
        return regenerate_hashes(manifest_path)
    return fetch(
        manifest_path=manifest_path,
        dest=Path(args.dest),
        verify_only=args.verify,
        offline=args.offline,
    )


if __name__ == "__main__":
    raise SystemExit(main())
