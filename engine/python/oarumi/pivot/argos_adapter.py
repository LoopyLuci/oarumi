"""Offline pivot translator backed by argostranslate, with graceful degradation."""

from __future__ import annotations

from dataclasses import dataclass

from oarumi.errors import CapabilityMissingError, OfflineError


@dataclass(slots=True)
class ArgosAdapter:
    offline: bool = False

    def _import(self) -> object:
        try:
            import argostranslate.translate  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CapabilityMissingError(
                "argostranslate is not installed", capability="argos"
            ) from exc
        return argostranslate.translate

    def available(self, src: str, dst: str = "en") -> bool:
        if self.offline:
            raise OfflineError("argos adapter invoked in offline mode")
        try:
            mod = self._import()
        except CapabilityMissingError:
            return False
        langs = mod.get_installed_languages()  # type: ignore[attr-defined]
        codes = {lang.code for lang in langs}
        return src in codes and dst in codes

    def translate(self, text: str, src: str, dst: str = "en") -> str:
        if self.offline:
            raise OfflineError("argos adapter invoked in offline mode")
        mod = self._import()
        try:
            return str(mod.translate(text, src, dst))  # type: ignore[attr-defined]
        except Exception as exc:
            raise CapabilityMissingError(
                f"argos translation failed for {src}->{dst}: {exc}", capability="argos"
            ) from exc
