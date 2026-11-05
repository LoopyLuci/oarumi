"""Keep known secret values out of log output.

The filter is a safety net, not the main defence: the code should never log a
value in the first place. It covers messages, arguments, and exception text.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Iterable, MutableMapping

REDACTED = "[REDACTED]"
# Very short values would blank out ordinary log text, so they are not redacted.
MIN_SECRET_LENGTH = 4


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        # Longest first, so a value that contains another is fully replaced.
        self._secrets = sorted(
            {s for s in secrets if len(s) >= MIN_SECRET_LENGTH},
            key=len,
            reverse=True,
        )

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = self.redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        if record.exc_info:
            trace = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = self.redact(trace)
        elif record.exc_text:
            record.exc_text = self.redact(record.exc_text)
        return True


def secrets_from_environ(environ: MutableMapping[str, str]) -> list[str]:
    """Secret-looking OARUMI_* values that are already in the environment."""
    from desktop.settings.registry import is_secret_name

    return [v for k, v in environ.items() if k.startswith("OARUMI_") and is_secret_name(k)]


def install_redaction(secrets: Iterable[str]) -> RedactingFilter:
    """Attach the filter to the root logger and its handlers.

    Logger-level filters do not see records that propagate from child loggers,
    so the filter is also attached to every handler.
    """
    values = list(secrets)
    redactor = RedactingFilter(values)
    root = logging.getLogger()
    root.addFilter(redactor)
    for handler in root.handlers:
        handler.addFilter(redactor)
    return redactor
