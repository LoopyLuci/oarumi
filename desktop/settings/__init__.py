"""Secure environment-variable settings for Oarumi.

Secrets go to the OS keychain, other values to a JSON file outside the repo.
See docs/SETTINGS.md for the security model.
"""

from desktop.settings.manager import EnvManager, default_manager
from desktop.settings.redact import install_redaction, secrets_from_environ
from desktop.settings.store import SecretBackendUnavailable, SettingsError

__all__ = [
    "EnvManager",
    "SecretBackendUnavailable",
    "SettingsError",
    "default_manager",
    "install_redaction",
    "secrets_from_environ",
]
