"""Modality renderers: spoken (TTS), signed (SiGML), tactile (protocol)."""

from oarumi.renderers.audio_assets import AudioAsset, AudioAssetLibrary
from oarumi.renderers.base import Renderer, RenderOutput
from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer, validate_sigml
from oarumi.renderers.tactile import TactileRenderer
from oarumi.renderers.tts import AssetTtsBackend, EspeakTtsBackend, TtsRenderer

__all__ = [
    "AssetTtsBackend",
    "AudioAsset",
    "AudioAssetLibrary",
    "EspeakTtsBackend",
    "HamNoSysToSigML",
    "RenderOutput",
    "Renderer",
    "SignRenderer",
    "TactileRenderer",
    "TtsRenderer",
    "validate_sigml",
]
