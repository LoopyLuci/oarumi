"""Orchestrate parity runs across targets.

Two targets are supported:
  - "python": in-process call to tools.parity_runner.run().
  - "kotlin": shell out to ./gradlew :engine:test, then read the JSON report
    emitted by oarumi.ParityTest (see § 0.1). Falls back to a JUnit XML
    summary if the report is absent.
"""

from __future__ import annotations

import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


class Runner:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.root = (repo_root or ROOT).resolve()

    async def run(
        self,
        run_id: str,
        corpus: str,
        targets: list[str],
        store: Any,
    ) -> None:
        store.mark_running(run_id)
        errors: list[str] = []

        for target in targets:
            store.mark_target_running(run_id, target)
            try:
                payload = await self._run_one(target, corpus)
                store.complete_target(run_id, target, payload=payload)
            except Exception as exc:
                msg = f"{target}: {type(exc).__name__}: {exc}"
                errors.append(msg)
                store.complete_target(run_id, target, error=msg)

        store.finish_run(run_id, error="; ".join(errors) if errors else None)

    # --- per-target dispatch --------------------------------------------

    async def _run_one(self, target: str, corpus: str) -> dict[str, Any]:
        if target == "python":
            return await self._run_python(corpus)
        if target in {"kotlin", "android"}:
            return await self._run_kotlin(corpus)
        raise ValueError(f"unknown target: {target!r}")

    async def _run_python(self, corpus: str) -> dict[str, Any]:
        from tools import parity_runner

        return await asyncio.to_thread(
            parity_runner.run,
            corpus,
            db_path=None,
            target="python",
            strict=False,
        )

    async def _run_kotlin(self, corpus: str) -> dict[str, Any]:
        gradlew = self.root / "android" / "gradlew"
        if not gradlew.exists():
            raise FileNotFoundError("android/gradlew not found")

        report_path = self.root / "android" / "build" / "parity-report.json"
        xml_dir = self.root / "android" / "engine" / "build" / "test-results" / "test"
        if xml_dir.exists():
            for f in xml_dir.glob("*.xml"):
                f.unlink()

        proc = await asyncio.create_subprocess_exec(
            str(gradlew),
            "--quiet",
            ":engine:test",
            "--tests",
            "oarumi.ParityTest",
            cwd=str(self.root / "android"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()

        # Prefer the explicit JSON report (§ 0.1).
        if report_path.exists():
            report: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
            return report

        # Fall back to JUnit XML: pass/fail counts only, no per-case got.
        if xml_dir.exists():
            return self._parse_junit(xml_dir, corpus)

        raise RuntimeError(
            f"gradle returned {proc.returncode}, no report at {report_path}; "
            f"stderr={stderr.decode('utf-8', 'replace')[:400]}"
        )

    @staticmethod
    def _parse_junit(xml_dir: Path, corpus: str) -> dict[str, Any]:
        cases: list[dict[str, Any]] = []
        for xml_path in sorted(xml_dir.glob("*.xml")):
            try:
                tree = ET.parse(xml_path)
            except ET.ParseError:
                continue
            for tc in tree.getroot().iter("testcase"):
                failure = tc.find("failure")
                cases.append(
                    {
                        "case_id": tc.get("name", ""),
                        "match": failure is None,
                        "error": (failure.text if failure is not None else None),
                    }
                )
        passed = sum(1 for c in cases if c["match"])
        return {
            "corpus": corpus,
            "target": "kotlin",
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "cases": cases,
            "note": "per-case 'got' not available; upgrade ParityTest to emit JSON (§ 0.1)",
        }
