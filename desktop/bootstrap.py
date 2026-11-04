"""Bootstrap: download optional Argos packs and TTS voices, verify hashes.

python -m desktop.bootstrap --check
python -m desktop.bootstrap --all
python -m desktop.bootstrap --langs es,fr
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "models" / "manifests" / "bootstrap.json"
DEFAULT_DEST = ROOT / "models" / "bootstrap"


@dataclass(slots=True)
class BootstrapStatus:
    asset_id: str
    kind: str
    installed: bool
    verified: bool
    path: Path | None

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.asset_id,
            "kind": self.kind,
            "installed": self.installed,
            "verified": self.verified,
            "path": str(self.path) if self.path else None,
        }


@dataclass(slots=True)
class Bootstrap:
    manifest_path: Path = DEFAULT_MANIFEST
    dest: Path = DEFAULT_DEST
    offline: bool = False
    _manifest: dict[str, Any] | None = field(default=None, init=False)

    def _load(self) -> dict[str, Any]:
        if self._manifest is None:
            if not self.manifest_path.exists():
                raise FileNotFoundError(f"bootstrap manifest missing: {self.manifest_path}")
            self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return self._manifest

    def status(self) -> list[BootstrapStatus]:
        manifest = self._load()
        out: list[BootstrapStatus] = []
        for asset in manifest.get("assets", []):
            asset_id = str(asset["id"])
            path = self.dest / asset_id
            installed = path.exists()
            verified = False
            if installed:
                expected = str(asset.get("sha256") or "")
                if expected:
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                    verified = actual == expected
                else:
                    # Unverified manifest: treat presence as ready for the phrasebook path.
                    verified = True
            out.append(
                BootstrapStatus(
                    asset_id=asset_id,
                    kind=str(asset.get("kind", "unknown")),
                    installed=installed,
                    verified=verified,
                    path=path if installed else None,
                )
            )
        return out

    def is_ready(self) -> bool:
        """True when every non-optional asset is installed and verified."""
        manifest = self._load()
        optional_ids = {str(a["id"]) for a in manifest.get("assets", []) if a.get("optional")}
        for s in self.status():
            if s.asset_id in optional_ids:
                continue
            if not (s.installed and s.verified):
                return False
        return True

    def install(self, lang_filter: set[str] | None = None) -> int:
        if self.offline:
            print("error: bootstrap refused: offline mode", file=sys.stderr)
            return 2
        manifest = self._load()
        self.dest.mkdir(parents=True, exist_ok=True)
        failures = 0

        for asset in manifest.get("assets", []):
            asset_id = str(asset["id"])
            if lang_filter is not None:
                pairs = asset.get("language_pair") or [asset.get("language", "")]
                if not any(p in lang_filter for p in pairs):
                    continue

            url = str(asset.get("url", ""))
            expected = str(asset.get("sha256") or "")
            target = self.dest / asset_id
            if (
                target.exists()
                and expected
                and hashlib.sha256(target.read_bytes()).hexdigest() == expected
            ):
                print(f"SKIP {asset_id} (already installed)")
                continue
            if not url or "example.invalid" in url:
                print(f"SKIP {asset_id} (no real URL configured)")
                continue

            try:
                self._download(url, target)
            except Exception as exc:
                print(f"FAIL {asset_id}: {exc}", file=sys.stderr)
                failures += 1
                continue

            if expected:
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual != expected:
                    print(f"FAIL {asset_id}: hash mismatch", file=sys.stderr)
                    target.unlink(missing_ok=True)
                    failures += 1
                    continue
            print(f"OK   {asset_id}")

        return 0 if failures == 0 else 1

    def _download(self, url: str, target: Path, timeout_s: float = 60.0) -> None:
        tmp = target.with_suffix(target.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            tmp.write_bytes(resp.read())
        tmp.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dest", default=str(DEFAULT_DEST))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report readiness; exit 1 if any required asset is missing",
    )
    parser.add_argument("--all", action="store_true", help="Install all assets")
    parser.add_argument("--langs", default=None, help="Comma-separated language codes to install")
    parser.add_argument("--offline", action="store_true", help="Refuse any network operation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    boot = Bootstrap(
        manifest_path=Path(args.manifest),
        dest=Path(args.dest),
        offline=args.offline,
    )

    try:
        if args.check:
            statuses = boot.status()
            if args.json:
                print(json.dumps([s.to_json() for s in statuses], indent=2))
            else:
                for s in statuses:
                    mark = "ready" if s.installed and s.verified else "MISSING"
                    print(f"{mark:8} {s.asset_id}  ({s.kind})")
            return 0 if boot.is_ready() else 1

        if args.all:
            return boot.install()
        if args.langs:
            return boot.install(lang_filter=set(args.langs.split(",")))

        parser.error("pass --check, --all, or --langs")
        return 2
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
