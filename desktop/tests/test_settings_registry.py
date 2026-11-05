"""Name rules, secret classification and value validation."""

from __future__ import annotations

import pytest

from desktop.settings.registry import (
    MAX_VALUE_LENGTH,
    REGISTRY,
    is_secret_name,
    validate_value,
    variable_for,
)


@pytest.mark.parametrize(
    "name", ["OARUMI_LOG_LEVEL", "OARUMI_X", "OARUMI_A1_B2", "OARUMI_PARITY_PORT"]
)
def test_valid_names_are_accepted_by_the_pattern(name: str) -> None:
    from desktop.settings.registry import NAME_RE

    assert NAME_RE.match(name)


@pytest.mark.parametrize(
    "name", ["oarumi_x", "PATH", "OARUMI_", "OARUMI_lower", "OARUMI_HAS SPACE", "X_OARUMI_Y"]
)
def test_invalid_names_are_rejected_by_the_pattern(name: str) -> None:
    from desktop.settings.registry import NAME_RE

    assert NAME_RE.match(name) is None


def test_secret_names_are_detected_by_hint_words() -> None:
    assert is_secret_name("OARUMI_API_TOKEN")
    assert is_secret_name("OARUMI_SIGNING_PASSWORD")
    assert is_secret_name("OARUMI_KEY")
    assert not is_secret_name("OARUMI_LOG_LEVEL")


def test_registered_secret_kind_is_secret_even_without_hint() -> None:
    var = variable_for("OARUMI_HOME")
    assert not var.secret
    custom_secret = type(var)("OARUMI_NOTE", "secret", "x")
    assert custom_secret.secret


def test_every_registered_name_is_valid() -> None:
    from desktop.settings.registry import NAME_RE

    assert all(NAME_RE.match(name) for name in REGISTRY)


def test_bool_accepts_only_zero_or_one() -> None:
    var = variable_for("OARUMI_OFFLINE")
    assert validate_value(var, "1") == "1"
    with pytest.raises(ValueError, match="must be 0 or 1"):
        validate_value(var, "yes")


def test_int_respects_range() -> None:
    var = variable_for("OARUMI_PARITY_PORT")
    assert validate_value(var, "8090") == "8090"
    with pytest.raises(ValueError, match="at most 65535"):
        validate_value(var, "70000")
    with pytest.raises(ValueError, match="whole number"):
        validate_value(var, "80a0")


def test_choice_must_be_listed() -> None:
    var = variable_for("OARUMI_LOG_LEVEL")
    assert validate_value(var, "DEBUG") == "DEBUG"
    with pytest.raises(ValueError, match="must be one of"):
        validate_value(var, "TRACE")


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("", "must not be empty"),
        ("a\nb", "single line"),
        ("a\x00b", "single line"),
        (" padded", "leading or trailing"),
        ("x" * (MAX_VALUE_LENGTH + 1), "longer than"),
    ],
)
def test_text_rules(value: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        validate_value(variable_for("OARUMI_CUSTOM"), value)


def test_error_messages_never_echo_the_value() -> None:
    secret = "tok-SUPERSECRET-123\nmore"
    with pytest.raises(ValueError) as excinfo:
        validate_value(variable_for("OARUMI_API_TOKEN"), secret)
    assert "SUPERSECRET" not in str(excinfo.value)
