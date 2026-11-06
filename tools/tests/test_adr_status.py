"""Every ADR states a status in its header, using a value the index can rely on."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / "docs" / "adr"
ADR_FILE_RE = re.compile(r"^\d{4}-[a-z0-9-]+\.md$")
STATUS_RE = re.compile(r"^- \*\*Status:\*\*[ \t]+([A-Za-z]+)", re.MULTILINE)
HEADER_LINES = 10
KNOWN_STATUSES = frozenset({"accepted", "superseded", "proposed"})


def _adr_files(directory: Path = ADR_DIR) -> list[Path]:
    return sorted(path for path in directory.glob("*.md") if ADR_FILE_RE.match(path.name))


def _status_problem(path: Path) -> str | None:
    header = "\n".join(path.read_text(encoding="utf-8").splitlines()[:HEADER_LINES])
    match = STATUS_RE.search(header)
    if match is None:
        return f"{path.name}: no '- **Status:**' line in the first {HEADER_LINES} lines"
    if match.group(1).lower() not in KNOWN_STATUSES:
        return f"{path.name}: unknown status '{match.group(1)}'"
    return None


def test_adr_directory_is_not_empty() -> None:
    assert _adr_files(), f"no ADRs found in {ADR_DIR}"


def test_adr_file_filter_skips_non_adr_markdown(tmp_path: Path) -> None:
    (tmp_path / "0001-first.md").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    assert _adr_files(tmp_path) == [tmp_path / "0001-first.md"]


@pytest.mark.parametrize("adr", _adr_files(), ids=lambda p: p.name)
def test_adr_declares_a_known_status(adr: Path) -> None:
    assert _status_problem(adr) is None


def test_status_word_is_case_insensitive_and_ignores_trailing_text(tmp_path: Path) -> None:
    adr = tmp_path / "0009-example.md"
    adr.write_text("# ADR-0009: Example\n\n- **Status:** ACCEPTED (2026-11-05)\n", encoding="utf-8")
    assert _status_problem(adr) is None


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("# ADR-0009: Missing\n\n## Context\n", "no '- **Status:**' line"),
        ("# ADR-0009: Draft\n\n- **Status:** Draft\n", "unknown status 'Draft'"),
        ("# ADR-0009: Late\n" + "\n" * 12 + "- **Status:** Accepted\n", "no '- **Status:**' line"),
    ],
)
def test_status_problem_is_reported(tmp_path: Path, body: str, expected: str) -> None:
    adr = tmp_path / "0009-example.md"
    adr.write_text(body, encoding="utf-8")
    problem = _status_problem(adr)
    assert problem is not None
    assert expected in problem
