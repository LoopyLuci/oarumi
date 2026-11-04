"""Pivot translator: source language -> English, with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

from oarumi.config import EngineConfig
from oarumi.errors import CapabilityMissingError, FallbackRequired, OfflineError
from oarumi.pivot import phrasebook
from oarumi.pivot.argos_adapter import ArgosAdapter
from oarumi.types import PivotResult, TraceEntry


@dataclass(slots=True)
class PivotTranslator:
    cfg: EngineConfig
    argos: ArgosAdapter = field(default_factory=ArgosAdapter)

    def __post_init__(self) -> None:
        # Bind offline flag from config to adapter.
        self.argos.offline = self.cfg.offline

    def translate(self, text: str, src: str, dst: str = "en") -> PivotResult:
        text = text.strip()
        if not text:
            return PivotResult(text="", lang=dst, source="passthrough")

        if src == dst:
            return PivotResult(
                text=text,
                lang=dst,
                source="passthrough",
                trace=(
                    TraceEntry(step="pivot", path="deterministic", reason="src==dst").to_json(),
                ),
            )

        # 1. Phrasebook first — deterministic, zero-latency, exact.
        hit = phrasebook.lookup(src, text)
        if hit is not None:
            return PivotResult(
                text=hit,
                lang=dst,
                source="phrasebook",
                trace=(
                    TraceEntry(
                        step="pivot", path="deterministic", reason="phrasebook-hit"
                    ).to_json(),
                ),
            )

        # 2. Argos, if available and not offline.
        if not self.cfg.offline:
            try:
                if self.argos.available(src, dst):
                    translated = self.argos.translate(text, src, dst)
                    return PivotResult(
                        text=translated,
                        lang=dst,
                        source="argos",
                        trace=(TraceEntry(step="pivot", path="neural", reason="argos").to_json(),),
                    )
            except (CapabilityMissingError, OfflineError):
                pass

        # 3. Nothing worked — signal the shield to record a fallback event.
        raise FallbackRequired(
            f"no pivot path for lang={src!r}, text={text[:40]!r}",
            component="pivot",
            trigger="unavailable",
        )
