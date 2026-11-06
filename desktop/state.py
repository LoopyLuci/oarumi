"""Application state: the engine, its renderers, and the last result."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.pipeline import Pipeline
from oarumi.reliability.audit_log import AuditLog
from oarumi.renderers.audio_assets import AudioAssetLibrary
from oarumi.renderers.base import RenderOutput
from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer
from oarumi.renderers.tactile import TactileRenderer
from oarumi.renderers.tts import TtsRenderer
from oarumi.types import OarumiSurface, TranslationResult

from desktop.packs import PackManager


@dataclass
class AppState:
    repo_root: Path
    cfg: EngineConfig
    db: LanguageDb
    pipeline: Pipeline
    audit: AuditLog
    tts: TtsRenderer
    sign: SignRenderer
    tactile: TactileRenderer
    last_result: TranslationResult | None = None
    _listeners: list[Callable[[TranslationResult], None]] = field(default_factory=list)
    packs: PackManager = field(default_factory=PackManager)

    @classmethod
    def from_env(cls, repo_root: Path) -> AppState:
        cfg = EngineConfig.from_env()
        db_path = repo_root / "language" / "oarumi.db"
        db = LanguageDb(db_path)

        audit = AuditLog(repo_root / ".oarumi-audit.jsonl")
        assets_dir = repo_root / "assets" / "audio"
        if not (assets_dir / "manifest.json").exists():
            raise FileNotFoundError(
                f"audio manifest missing at {assets_dir / 'manifest.json'}; "
                f"run `python tools/generate_audio_assets.py`"
            )
        try:
            audio = AudioAssetLibrary(assets_dir, require_verified=False)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"audio assets incomplete: {exc}. " f"Run `python tools/generate_audio_assets.py`."
            ) from exc

        tts = TtsRenderer(audio=audio)
        sign = SignRenderer(converter=HamNoSysToSigML(use_external=True))
        tactile = TactileRenderer()

        pipeline = Pipeline(db=db, cfg=cfg)
        pipeline.register_renderer("spoken", lambda s: _render(tts, s))
        pipeline.register_renderer("signed", lambda s: _render(sign, s))
        pipeline.register_renderer("tactile", lambda s: _render(tactile, s))

        return cls(
            repo_root=repo_root,
            cfg=cfg,
            db=db,
            pipeline=pipeline,
            audit=audit,
            tts=tts,
            sign=sign,
            tactile=tactile,
        )

    def close(self) -> None:
        self.db.close()

    # --- result broadcasting -------------------------------------------

    def set_last_result(self, result: TranslationResult) -> None:
        self.last_result = result
        for listener in list(self._listeners):
            # A broken view must not stop other listeners from updating.
            with contextlib.suppress(Exception):
                listener(result)

    def on_result(self, listener: Callable[[TranslationResult], None]) -> None:
        self._listeners.append(listener)


def _render(renderer: object, surface: OarumiSurface) -> dict[str, object]:
    out = renderer.render(surface)  # type: ignore[attr-defined]
    assert isinstance(out, RenderOutput)
    return out.to_json()
