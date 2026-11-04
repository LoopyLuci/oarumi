"""Dataclasses for the cross-language contracts C1–C3. JSON round-trip is mandatory."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

Modality = Literal["spoken", "signed", "tactile", "text"]
SourceKind = Literal["argos", "mlkit", "phrasebook", "passthrough"]
PrimRole = Literal["agent", "patient", "predicate", "modifier", "argument", "operator"]
CombinatorType = Literal["clause", "predicate", "modifier", "quote", "conditional"]
TracePath = Literal["deterministic", "neural"]
MoodCode = Literal["DECL", "INTERR", "IMPER", "PROM", "EXPRESS", "VOC"]


@dataclass(slots=True, frozen=True)
class PrimeRef:
    id: str
    role: PrimRole

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "role": self.role}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PrimeRef:
        return cls(id=str(data["id"]), role=data["role"])


@dataclass(slots=True, frozen=True)
class Combinator:
    type: CombinatorType
    head: str
    args: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {"type": self.type, "head": self.head, "args": list(self.args)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Combinator:
        return cls(
            type=data["type"],
            head=str(data["head"]),
            args=tuple(str(a) for a in data.get("args", [])),
        )


@dataclass(slots=True, frozen=True)
class NSMStructure:
    """Contract C1."""

    primes: tuple[PrimeRef, ...]
    combinators: tuple[Combinator, ...]
    valid: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "primes": [p.to_json() for p in self.primes],
            "combinators": [c.to_json() for c in self.combinators],
            "valid": self.valid,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> NSMStructure:
        return cls(
            primes=tuple(PrimeRef.from_json(p) for p in data["primes"]),
            combinators=tuple(Combinator.from_json(c) for c in data["combinators"]),
            valid=bool(data.get("valid", True)),
        )


@dataclass(slots=True, frozen=True)
class Clitic:
    form: str
    type: str

    def to_json(self) -> dict[str, Any]:
        return {"form": self.form, "type": self.type}


@dataclass(slots=True, frozen=True)
class OarumiSurface:
    """Contract C2."""

    phonemes: tuple[str, ...]
    clitics: tuple[Clitic, ...]
    mood: MoodCode
    modality: Modality

    def to_json(self) -> dict[str, Any]:
        return {
            "phonemes": list(self.phonemes),
            "clitics": [c.to_json() for c in self.clitics],
            "mood": self.mood,
            "modality": self.modality,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> OarumiSurface:
        return cls(
            phonemes=tuple(str(p) for p in data["phonemes"]),
            clitics=tuple(Clitic(form=c["form"], type=c["type"]) for c in data["clitics"]),
            mood=data["mood"],
            modality=data["modality"],
        )

    def to_string(self) -> str:
        """Deterministic string form used by round-trip tests."""
        return " ".join(self.phonemes)


@dataclass(slots=True, frozen=True)
class TranslationRequest:
    text: str
    lang: str
    modality: Modality = "spoken"
    target_modality: Modality | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "text": self.text,
            "lang": self.lang,
            "modality": self.modality,
        }
        if self.target_modality is not None:
            out["target_modality"] = self.target_modality
        return out


@dataclass(slots=True, frozen=True)
class PivotResult:
    text: str
    lang: str
    source: SourceKind
    trace: tuple[dict[str, Any], ...] = ()


@dataclass(slots=True, frozen=True)
class TraceEntry:
    step: str
    path: TracePath
    reason: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "path": self.path, "reason": self.reason}


@dataclass(slots=True, frozen=True)
class FailoverEvent:
    component: str
    trigger: str
    t: str

    def to_json(self) -> dict[str, Any]:
        return {"component": self.component, "trigger": self.trigger, "t": self.t}


@dataclass(slots=True, frozen=True)
class ModalityOutput:
    spoken: dict[str, Any] | None = None
    signed: dict[str, Any] | None = None
    tactile: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.spoken is not None:
            out["spoken"] = self.spoken
        if self.signed is not None:
            out["signed"] = self.signed
        if self.tactile is not None:
            out["tactile"] = self.tactile
        return out


@dataclass(slots=True)
class TranslationResult:
    """Contract C3. Uses plain dicts for sub-structures so renderers can extend them."""

    request_id: str
    input: dict[str, Any]
    pivot: dict[str, Any]
    nsm: NSMStructure
    surface: OarumiSurface
    modalities: dict[str, dict[str, Any]] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    failover_events: list[dict[str, Any]] = field(default_factory=list)
    degraded: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "input": self.input,
            "pivot": self.pivot,
            "nsm": self.nsm.to_json(),
            "surface": self.surface.to_json(),
            "modalities": self.modalities,
            "trace": self.trace,
            "failover_events": self.failover_events,
            "degraded": self.degraded,
        }

    @classmethod
    def new(
        cls,
        request: TranslationRequest,
        pivot: PivotResult,
        nsm: NSMStructure,
        surface: OarumiSurface,
    ) -> TranslationResult:
        return cls(
            request_id=str(uuid.uuid4()),
            input=request.to_json(),
            pivot={"text": pivot.text, "lang": pivot.lang, "source": pivot.source},
            nsm=nsm,
            surface=surface,
            trace=[t for t in pivot.trace],
        )


RouteKind = Literal["direct_deterministic", "neural_candidate", "refuse"]


@dataclass(slots=True, frozen=True)
class Route:
    kind: RouteKind
    reason: str
    capabilities: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reason": self.reason,
            "capabilities": list(self.capabilities),
        }


@dataclass(slots=True, frozen=True)
class ValidationOutcome:
    """Result of a validator run over an NSM structure or rendered surface."""

    valid: bool
    errors: tuple[str, ...] = ()
