"""Log redaction: secret values never reach a log line or traceback."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator

import pytest

from desktop.settings.redact import (
    REDACTED,
    RedactingFilter,
    install_redaction,
    secrets_from_environ,
)


def _logger_with(redactor: RedactingFilter) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(redactor)
    logger = logging.getLogger(f"test.redact.{id(redactor)}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream


def test_message_and_arguments_are_redacted() -> None:
    logger, stream = _logger_with(RedactingFilter(["hunter2-secret"]))
    logger.warning("connecting with %s", "hunter2-secret")
    logger.warning("plain text %s", "fine")
    output = stream.getvalue()
    assert "hunter2-secret" not in output
    assert REDACTED in output
    assert "plain text fine" in output


def test_traceback_text_is_redacted() -> None:
    logger, stream = _logger_with(RedactingFilter(["hunter2-secret"]))
    try:
        raise ValueError("failed with hunter2-secret inside")
    except ValueError:
        logger.exception("request failed")
    assert "hunter2-secret" not in stream.getvalue()


def test_short_values_are_not_redacted() -> None:
    redactor = RedactingFilter(["ab", "xyz"])
    assert redactor.redact("ab xyz") == "ab xyz"


def test_longest_value_is_replaced_first() -> None:
    redactor = RedactingFilter(["abcd", "abcdefgh"])
    assert redactor.redact("value abcdefgh here") == f"value {REDACTED} here"


def test_secret_in_a_child_logger_is_caught_by_the_handler() -> None:
    redactor = RedactingFilter(["hunter2-secret"])
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(redactor)
    parent = logging.getLogger("test.redact.parent")
    child = logging.getLogger("test.redact.parent.child")
    parent.handlers = [handler]
    parent.propagate = False
    parent.setLevel(logging.DEBUG)
    child.warning("token %s", "hunter2-secret")
    assert "hunter2-secret" not in stream.getvalue()


@pytest.fixture()
def root_clean() -> Iterator[None]:
    root = logging.getLogger()
    before_filters = list(root.filters)
    before_handlers = [(h, list(h.filters)) for h in root.handlers]
    yield
    for f in list(root.filters):
        if f not in before_filters:
            root.removeFilter(f)
    for handler, filters in before_handlers:
        for f in list(handler.filters):
            if f not in filters:
                handler.removeFilter(f)


def test_install_attaches_to_root_and_its_handlers(root_clean: None) -> None:
    redactor = install_redaction(["hunter2-secret"])
    root = logging.getLogger()
    assert redactor in root.filters
    for handler in root.handlers:
        assert redactor in handler.filters


def test_secrets_from_environ_picks_only_secret_looking_oarumi_names() -> None:
    environ = {
        "OARUMI_API_TOKEN": "tok-value",
        "OARUMI_LOG_LEVEL": "DEBUG",
        "PATH": "/usr/bin",
        "OTHER_TOKEN": "not-ours",
    }
    assert secrets_from_environ(environ) == ["tok-value"]
