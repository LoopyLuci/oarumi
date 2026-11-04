"""End-to-end pipeline: request -> pivot -> NSM -> surface -> modality outputs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.errors import FallbackRequired, OarumiError, ValidationError
from oarumi.nsm.decomposer import NSMDecomposerTierA
from oarumi.nsm.realizer import NSMRealizer
from oarumi.nsm.validator import NSMValidator
from oarumi.pivot.translator import PivotTranslator
from oarumi.reliability.intent_router import IntentRouter, StaticCapabilitySource
from oarumi.types import (
    NSMStructure,
    OarumiSurface,
    TranslationRequest,
    TranslationResult,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Pipeline:
    db: LanguageDb
    cfg: EngineConfig
    pivot: PivotTranslator | None = None
    decomposer: NSMDecomposerTierA | None = None
    realizer: NSMRealizer | None = None
    validator: NSMValidator | None = None
    router: IntentRouter | None = None
    _renderers: dict[str, Callable[[OarumiSurface], dict[str, object]]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.pivot is None:
            self.pivot = PivotTranslator(cfg=self.cfg)
        if self.decomposer is None:
            self.decomposer = NSMDecomposerTierA(db=self.db)
        if self.realizer is None:
            self.realizer = NSMRealizer(db=self.db)
        if self.validator is None:
            self.validator = NSMValidator(db=self.db)
        if self.router is None:
            self.router = IntentRouter(
                source=StaticCapabilitySource(db=self.db, offline=self.cfg.offline),
            )

    def register_renderer(
        self, modality: str, fn: Callable[[OarumiSurface], dict[str, object]]
    ) -> None:
        self._renderers[modality] = fn

    def translate(self, req: TranslationRequest) -> TranslationResult:
        assert self.pivot is not None
        assert self.decomposer is not None
        assert self.realizer is not None
        assert self.validator is not None
        assert self.router is not None

        # 0. Router: refuse early so downstream steps see a stable contract (mirrors Kotlin).
        route = self.router.route(req)
        if route.kind == "refuse":
            return TranslationResult(
                request_id="",
                input=req.to_json(),
                pivot={"text": "", "lang": "en", "source": "phrasebook"},
                nsm=NSMStructure(primes=(), combinators=(), valid=False),
                surface=OarumiSurface(phonemes=(), clitics=(), mood="DECL", modality=req.modality),
                trace=[{"step": "intent", "path": "deterministic", "reason": route.reason}],
                failover_events=[
                    {"component": "intent_router", "trigger": route.reason, "t": _now()}
                ],
                degraded=True,
            )

        failover: list[dict[str, object]] = []

        try:
            pivot = self.pivot.translate(req.text, req.lang, "en")
        except FallbackRequired as exc:
            empty_nsm = NSMStructure(primes=(), combinators=(), valid=False)
            empty_surface = OarumiSurface(
                phonemes=(), clitics=(), mood="DECL", modality=req.modality
            )
            return TranslationResult(
                request_id="",
                input=req.to_json(),
                pivot={"text": "", "lang": "en", "source": "phrasebook"},
                nsm=empty_nsm,
                surface=empty_surface,
                trace=[],
                failover_events=[{"component": exc.component, "trigger": exc.trigger, "t": _now()}],
                degraded=True,
            )

        try:
            nsm = self.decomposer.decompose(pivot.text)
        except ValidationError:
            failover.append({"component": "nsm_decompose", "trigger": "validation", "t": _now()})
            empty = NSMStructure(primes=(), combinators=(), valid=False)
            surface = OarumiSurface(phonemes=(), clitics=(), mood="DECL", modality=req.modality)
            return TranslationResult(
                request_id="",
                input=req.to_json(),
                pivot={"text": pivot.text, "lang": pivot.lang, "source": pivot.source},
                nsm=empty,
                surface=surface,
                trace=list(pivot.trace),
                failover_events=failover,
                degraded=True,
            )

        outcome = self.validator.validate(nsm)
        if not outcome.valid:
            failover.append({"component": "nsm_validate", "trigger": "validation", "t": _now()})
            nsm = NSMStructure(primes=nsm.primes, combinators=nsm.combinators, valid=False)

        surface = self.realizer.realize(nsm, modality=req.modality)

        modalities: dict[str, dict[str, object]] = {}
        targets = [req.modality]
        if req.target_modality is not None and req.target_modality != req.modality:
            targets.append(req.target_modality)
        for m in targets:
            renderer = self._renderers.get(m)
            if renderer is None:
                continue
            try:
                modalities[m] = renderer(surface)
            except OarumiError:
                failover.append({"component": f"render_{m}", "trigger": "unavailable", "t": _now()})

        result = TranslationResult.new(request=req, pivot=pivot, nsm=nsm, surface=surface)
        result.modalities = modalities
        result.failover_events.extend(failover)
        result.degraded = bool(failover) or not nsm.valid
        return result
