"""docs/PARITY_API.md must match the live Python engine."""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "PARITY_API.md"

# Where each documented Python class lives.
MODULES = {
    "LanguageDb": "oarumi.db",
    "PivotTranslator": "oarumi.pivot.translator",
    "NSMDecomposerTierA": "oarumi.nsm.decomposer",
    "NSMRealizer": "oarumi.nsm.realizer",
    "Pipeline": "oarumi.pipeline",
}

ROW = re.compile(r"^\| `(?P<cls>\w+)` \| `(?P<meth>\w+)` \| `(?P<sig>.+)` \|$")


def _python_rows() -> list[tuple[str, str, str]]:
    text = DOC.read_text(encoding="utf-8")
    section = text.split("## Python", 1)[1].split("## Kotlin", 1)[0]
    return [
        (m["cls"], m["meth"], m["sig"])
        for m in (ROW.match(line) for line in section.splitlines())
        if m
    ]


def test_parity_doc_lists_every_python_class() -> None:
    documented = {cls for cls, _, _ in _python_rows()}
    assert documented == set(MODULES)


def test_documented_python_methods_exist_with_documented_parameters() -> None:
    for cls_name, meth, sig in _python_rows():
        owner = getattr(importlib.import_module(MODULES[cls_name]), cls_name)
        method = getattr(owner, meth)
        actual = [p for p in inspect.signature(method).parameters if p != "self"]
        documented = re.findall(r"(\w+)\s*:", sig)
        assert actual[: len(documented)] == documented, f"{cls_name}.{meth}: {sig}"
