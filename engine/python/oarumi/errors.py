"""Oarumi exception hierarchy. Every error is typed; no bare Exception escapes."""

from __future__ import annotations


class OarumiError(Exception):
    """Base class for all Oarumi errors."""


class ValidationError(OarumiError):
    """A structural or semantic invariant was violated."""

    def __init__(self, message: str, *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []


class FallbackRequired(OarumiError):
    """The current path cannot serve this input; the deterministic twin must take over."""

    def __init__(self, message: str, *, component: str, trigger: str) -> None:
        super().__init__(message)
        self.component = component
        self.trigger = trigger


class OfflineError(OarumiError):
    """A network call was attempted while the engine is in offline mode."""


class IntegrityError(OarumiError):
    """A model or asset hash did not match its manifest."""


class CapabilityMissingError(OarumiError):
    """The requested capability (language, model, voice) is not installed."""

    def __init__(self, message: str, *, capability: str) -> None:
        super().__init__(message)
        self.capability = capability
