"""Shared fixtures for parity tests. Loads config, DB, and helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PARITY_ROOT = Path(__file__).resolve().parent
DATA = PARITY_ROOT / "data"
CONFIG = PARITY_ROOT / "config.yaml"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--parity-corpus",
        action="store",
        default="parity-basic",
        help="Corpus directory name under tests/parity/data/",
    )
    parser.addoption(
        "--parity-strict",
        action="store_true",
        help="Treat missing expected output as failure (default: skip).",
    )


@pytest.fixture(scope="session")
def parity_config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def parity_data_dir() -> Path:
    return DATA


@pytest.fixture(scope="session")
def parity_corpus(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--parity-corpus")


@pytest.fixture(scope="session")
def parity_strict(request: pytest.FixtureRequest) -> bool:
    env_strict = os.environ.get("OARUMI_STRICT_PARITY") == "1"
    return request.config.getoption("--parity-strict") or env_strict


@pytest.fixture(scope="session")
def parity_cases(parity_corpus: str, parity_data_dir: Path) -> list[tuple[str, dict]]:
    """Return [(case_id, case_dict), ...] for the selected corpus."""
    corpus_dir = parity_data_dir / parity_corpus
    if not corpus_dir.exists():
        pytest.skip(f"corpus not found: {corpus_dir}")
    cases: list[tuple[str, dict]] = []
    for path in sorted(corpus_dir.glob("*.json")):
        cases.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
    if not cases:
        pytest.skip(f"corpus empty: {corpus_dir}")
    return cases


def canonicalise(result: dict) -> dict:
    """Mirror of tools.parity_runner._canonical: strip ephemeral fields."""
    out = json.loads(json.dumps(result))
    out.pop("request_id", None)
    for ev in out.get("failover_events", []):
        ev.pop("t", None)
    for payload in out.get("modalities", {}).values():
        payload.pop("audio_path", None)
        payload.pop("duration_ms", None)
        if payload.get("backend") in {"espeak", "android", "native"}:
            payload["backend"] = "native"
    return out
