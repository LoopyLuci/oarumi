"""Update checks against GitHub Releases.

Only metadata is fetched here. Downloading and installing a new build is the
caller's job, and on Android it happens only after a checksum matches. The
Kotlin port is android/app/src/main/java/com/oarumi/app/data/update/ReleaseParser.kt.
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

RELEASES_LATEST_URL = "https://api.github.com/repos/LoopyLuci/oarumi/releases/latest"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True, slots=True)
class Version:
    core: tuple[int, int, int]
    pre: tuple[int | str, ...]

    def __lt__(self, other: Version) -> bool:
        if self.core != other.core:
            return self.core < other.core
        if self.pre == other.pre:
            return False
        if not self.pre:
            return False
        if not other.pre:
            return True
        return _pre_key(self.pre) < _pre_key(other.pre)


def _pre_key(pre: tuple[int | str, ...]) -> tuple[tuple[int, int | str], ...]:
    # Numeric identifiers sort before alphanumeric ones, as in SemVer.
    return tuple((0, part) if isinstance(part, int) else (1, part) for part in pre)


def parse_version(text: str) -> Version:
    """Parse `v0.1.0-alpha.4` or `0.1.0` into a comparable Version."""
    body = text.strip()
    if body[:1] in ("v", "V"):
        body = body[1:]
    body = body.split("+", 1)[0]
    core_text, _, pre_text = body.partition("-")
    parts = core_text.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"not a version: {text!r}")
    core = (int(parts[0]), int(parts[1]), int(parts[2]))
    pre: tuple[int | str, ...] = ()
    if pre_text:
        pre = tuple(int(part) if part.isdigit() else part for part in pre_text.split("."))
    return Version(core=core, pre=pre)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(current) < parse_version(latest)


_PEP440_ALPHA = re.compile(r"(\d+\.\d+\.\d+)(?:a(\d+))?")


def to_semver(text: str) -> str:
    """Map a Python package version such as `0.1.0a4` onto the release tag form `0.1.0-alpha.4`."""
    match = _PEP440_ALPHA.fullmatch(text.strip())
    if match is None:
        return text
    suffix = f"-alpha.{match.group(2)}" if match.group(2) else ""
    return match.group(1) + suffix


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    url: str
    size_bytes: int
    sha256: str | None


@dataclass(frozen=True, slots=True)
class Release:
    tag: str
    html_url: str
    assets: tuple[ReleaseAsset, ...]

    @property
    def version(self) -> Version:
        return parse_version(self.tag)


def parse_release(data: Mapping[str, Any]) -> Release:
    assets: list[ReleaseAsset] = []
    for item in data.get("assets", []):
        digest = item.get("digest")
        sha256 = (
            digest.split(":", 1)[1]
            if isinstance(digest, str) and digest.startswith("sha256:")
            else None
        )
        assets.append(
            ReleaseAsset(
                name=str(item["name"]),
                url=str(item["browser_download_url"]),
                size_bytes=int(item.get("size", 0)),
                sha256=sha256,
            )
        )
    return Release(tag=str(data["tag_name"]), html_url=str(data["html_url"]), assets=tuple(assets))


def pick_apk(release: Release, flavor: str, build_type: str = "release") -> ReleaseAsset | None:
    """The APK for one flavor. Names follow android/app/build.gradle.kts."""
    prefix = f"oarumi-{flavor}-{build_type}-"
    for asset in release.assets:
        if asset.name.startswith(prefix) and asset.name.endswith(".apk"):
            return asset
    return None


def fetch_latest(url: str = RELEASES_LATEST_URL) -> Release:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    return parse_release(data)
