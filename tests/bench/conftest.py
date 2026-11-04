"""Benchmark fixtures. Uses the same seeded DB and renderers as the app."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def bench_db():
    from oarumi.db import LanguageDb

    path = ROOT / "language" / "oarumi.db"
    if not path.exists():
        pytest.skip("language DB missing; run ./scripts/bootstrap.sh")
    return LanguageDb(path)


@pytest.fixture(scope="session")
def bench_pipeline(bench_db):
    from oarumi.config import EngineConfig
    from oarumi.pipeline import Pipeline
    from oarumi.renderers.audio_assets import AudioAssetLibrary
    from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer
    from oarumi.renderers.tactile import TactileRenderer
    from oarumi.renderers.tts import TtsRenderer

    cfg = EngineConfig.from_env()
    pipeline = Pipeline(db=bench_db, cfg=cfg)

    audio_dir = ROOT / "assets" / "audio"
    if (audio_dir / "manifest.json").exists():
        audio = AudioAssetLibrary(audio_dir, require_verified=False)
        tts = TtsRenderer(audio=audio, espeak_bin=None)
        pipeline.register_renderer("spoken", lambda s: tts.render(s).to_json())

    sign = SignRenderer(converter=HamNoSysToSigML(use_external=False))
    pipeline.register_renderer("signed", lambda s: sign.render(s).to_json())
    pipeline.register_renderer("tactile", lambda s: TactileRenderer().render(s).to_json())
    return pipeline
