"""Tactile renderer: OarumiSurface -> four-hand reciprocal protocol.

Batch 4 uses a deterministic mapping from mood + clitic shape to a construction.
When the NSM structure is available, callers may pass `nsm=` to refine the
mapping; Batch 7 wires that refinement into the Android engine.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from oarumi.renderers.base import RenderOutput
from oarumi.types import OarumiSurface

# Deterministic construction catalogue (mirrors language/tactile/protactile.yaml).
CONSTRUCTIONS: dict[str, dict[str, Any]] = {
    "T001": {
        "conveyer_hand": "right",
        "receiver_location": "left_forearm",
        "movement": "linear",
        "contact": "light",
        "gloss": "referent_established",
    },
    "T002": {
        "conveyer_hand": "left",
        "receiver_location": "right_forearm",
        "movement": "circular",
        "contact": "firm",
        "gloss": "location_here",
    },
    "T003": {
        "conveyer_hand": "both",
        "receiver_location": "chest",
        "movement": "tap",
        "contact": "light",
        "gloss": "self_reference",
    },
    "T004": {
        "conveyer_hand": "right",
        "receiver_location": "left_palm",
        "movement": "hold",
        "contact": "firm",
        "gloss": "object_given",
    },
    "T005": {
        "conveyer_hand": "left",
        "receiver_location": "right_shoulder",
        "movement": "press",
        "contact": "firm",
        "gloss": "attention_request",
    },
}


@dataclass(slots=True)
class TactileRenderer:
    modality: str = "tactile"

    def render(self, surface: OarumiSurface, **kwargs: Any) -> RenderOutput:
        cid = self._select(surface)
        base = dict(CONSTRUCTIONS[cid])
        referent = _referent_id(surface)
        protocol = {
            "construction_id": cid,
            "conveyer_hand": base["conveyer_hand"],
            "receiver_location": base["receiver_location"],
            "movement": base["movement"],
            "contact": base["contact"],
            "referent_id": referent,
            "gloss": base["gloss"],
        }
        errors = self._validate(protocol)
        return RenderOutput(
            modality=self.modality,
            payload={"protocol": protocol},
            valid=not errors,
            errors=tuple(errors),
        )

    def _select(self, surface: OarumiSurface) -> str:
        forms = {c.type for c in surface.clitics}
        tokens = set(surface.phonemes)
        if surface.mood == "INTERR":
            if "lonu" in tokens or "where" in tokens:
                return "T002"
            return "T005"
        if surface.mood == "IMPER":
            return "T004"
        if surface.mood == "PROM":
            return "T003"
        if surface.mood == "EXPRESS":
            return "T005"
        if surface.mood == "VOC":
            return "T003"
        if "mood_declarative" in forms:
            return "T001"
        return "T001"

    @staticmethod
    def _validate(protocol: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        required = {
            "construction_id",
            "conveyer_hand",
            "receiver_location",
            "movement",
            "contact",
            "referent_id",
        }
        missing = required - protocol.keys()
        if missing:
            errors.extend(f"missing:{k}" for k in sorted(missing))
        if protocol.get("conveyer_hand") not in {"left", "right", "both"}:
            errors.append("bad_conveyer_hand")
        if protocol.get("contact") not in {"light", "firm"}:
            errors.append("bad_contact")
        return errors


def _referent_id(surface: OarumiSurface) -> str:
    h = hashlib.sha256("|".join(surface.phonemes).encode("utf-8")).hexdigest()
    return f"r{h[:8]}"
