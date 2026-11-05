"""Every shipped version string must name the same release."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from oarumi.updates import to_semver

ROOT = Path(__file__).resolve().parents[2]
PYTHON_VERSION_FILES = (
    ROOT / "engine" / "python" / "oarumi" / "__init__.py",
    ROOT / "desktop" / "__init__.py",
    ROOT / "tools" / "__init__.py",
    ROOT / "tools" / "parity_web" / "__init__.py",
)
PYTHON_VERSION_RE = re.compile(r'^__version__ = "([^"]+)"', re.MULTILINE)
GRADLE_FILE = ROOT / "android" / "app" / "build.gradle.kts"
VERSION_NAME_RE = re.compile(r'versionName = "([^"]+)"')


def _package_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_python_packages_share_the_package_version() -> None:
    expected = _package_version()
    for path in PYTHON_VERSION_FILES:
        match = PYTHON_VERSION_RE.search(path.read_text(encoding="utf-8"))
        assert match is not None, path.relative_to(ROOT).as_posix()
        assert match.group(1) == expected, path.relative_to(ROOT).as_posix()


def test_android_version_name_matches_the_release_tag() -> None:
    match = VERSION_NAME_RE.search(GRADLE_FILE.read_text(encoding="utf-8"))
    assert match is not None
    assert match.group(1) == to_semver(_package_version())
