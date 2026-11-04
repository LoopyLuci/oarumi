"""Renderer protocol and the RenderOutput envelope.

A renderer maps an OarumiSurface to a modality-specific payload. It never
raises for a well-formed surface; instead it returns valid=False and lists
errors, so the pipeline can record a deterministic degradation instead of a
crash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from oarumi.types import OarumiSurface


@dataclass(slots=True, frozen=True)
class RenderOutput:
    modality: str
    payload: dict[str, Any] = field(default_factory=dict)
    valid: bool = True
    errors: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"modality": self.modality}
        out.update(self.payload)
        out["valid"] = self.valid
        if self.errors:
            out["errors"] = list(self.errors)
        return out


class Renderer(Protocol):
    modality: str

    def render(self, surface: OarumiSurface, **kwargs: Any) -> RenderOutput: ...
