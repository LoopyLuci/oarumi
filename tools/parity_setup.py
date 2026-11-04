"""Build the parity pipeline exactly as the test fixtures and the gold freezer need it.

Single source of truth: tests/parity/conftest.py and tools/freeze_gold.py both call
`build_pipeline`, so frozen gold always reflects the renderers the tests exercise.
"""

from __future__ import annotations

from pathlib import Path

from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.pipeline import Pipeline
from oarumi.renderers.audio_assets import AudioAssetLibrary
from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer
from oarumi.renderers.tactile import TactileRenderer
from oarumi.renderers.tts import TtsRenderer

ROOT = Path(__file__).resolve().parent.parent


def build_pipeline(db: LanguageDb, root: Path = ROOT) -> Pipeline:
    """Return a pipeline with the deterministic spoken/signed/tactile renderers.

    Raises FileNotFoundError when the audio manifest is missing; callers skip or fail.
    """
    audio_dir = root / "assets" / "audio"
    if not (audio_dir / "manifest.json").exists():
        raise FileNotFoundError(f"audio manifest missing under {audio_dir}")

    pipeline = Pipeline(db=db, cfg=EngineConfig.from_env())
    audio = AudioAssetLibrary(audio_dir, require_verified=False)
    tts = TtsRenderer(audio=audio, espeak_bin=None)  # deterministic asset backend
    pipeline.register_renderer("spoken", lambda s: tts.render(s).to_json())

    sign = SignRenderer(converter=HamNoSysToSigML(use_external=False))
    pipeline.register_renderer("signed", lambda s: sign.render(s).to_json())
    pipeline.register_renderer("tactile", lambda s: TactileRenderer().render(s).to_json())
    return pipeline
