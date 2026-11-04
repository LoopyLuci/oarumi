"""Assert every markdown link in the repo resolves to a file or URL."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".gradle",
    ".idea",
    ".pytest_cache",
    "models",
    "android/build",
    "android/app/build",
    "android/engine/build",
    "tests/parity/data",
}

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _md_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT).as_posix()
        if any(rel == skip or rel.startswith(skip + "/") for skip in SKIP_DIRS):
            continue
        if any(skip in path.parts for skip in SKIP_DIRS if "/" not in skip):
            continue
        files.append(path)
    return files


def _strip_code(text: str) -> str:
    text = CODE_FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def _check_link(source: Path, target: str) -> tuple[bool, str]:
    target = target.split("#", 1)[0].strip()
    if not target:
        return True, ""
    if target.startswith(("http://", "https://", "mailto:", "tel:")):
        return True, ""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    resolved = (source.parent / target).resolve()
    if not resolved.is_relative_to(ROOT):
        # GitHub-relative links such as ../../releases only resolve on the forge.
        return True, ""
    if not resolved.exists():
        return False, f"{source.relative_to(ROOT)}: link '{target}' → missing {resolved}"
    return True, ""


@pytest.mark.parametrize("md_file", _md_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_links_resolve(md_file: Path) -> None:
    text = _strip_code(md_file.read_text(encoding="utf-8"))
    problems: list[str] = []
    for match in LINK_RE.finditer(text):
        target = match.group(2)
        ok, err = _check_link(md_file, target)
        if not ok:
            problems.append(err)
    assert not problems, "\n".join(problems)
