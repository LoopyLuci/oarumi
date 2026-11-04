"""Signed renderer: HamNoSys->SiGML, structural validation, 50 cases."""

from __future__ import annotations

import pytest
from oarumi.renderers.sign import (
    ALLOWED_SYMBOLS,
    HamNoSysToSigML,
    SignRenderer,
    validate_sigml,
)
from oarumi.types import Clitic, OarumiSurface

VALID_ANNOTATIONS = [
    "sym:hamfinger2 sym:hamthumbout sym:hamnohandchange sym:hamarcsym sym:hamextfingeru",
    "sym:hamfinger2 sym:hampalmd sym:hamchest sym:hammoveo",
    "sym:hamfinger2 sym:hamthumbout sym:hamhead sym:hammoved",
    "sym:hamfinger2 sym:hamshoulders sym:hamrepeat",
    "sym:hamfinger2 sym:hamwaist sym:hamtouch",
]


def _surface() -> OarumiSurface:
    return OarumiSurface(
        phonemes=("manu",),
        clitics=(Clitic(form="=ha", type="mood_declarative"),),
        mood="DECL",
        modality="signed",
    )


@pytest.mark.parametrize("annotation", VALID_ANNOTATIONS * 10)
def test_convert_produces_valid_sigml(annotation: str) -> None:
    xml = HamNoSysToSigML(use_external=False).convert(annotation, gloss="test")
    ok, errors = validate_sigml(xml)
    assert ok, errors
    assert "hns_sign" in xml
    assert 'gloss="test"' in xml


def test_unknown_symbol_is_invalid() -> None:
    xml = HamNoSysToSigML(use_external=False).convert("sym:hamnotarealsymbol")
    ok, errors = validate_sigml(xml)
    assert not ok
    assert any("unknown_symbol" in e for e in errors)


def test_renderer_uses_default_when_no_annotation() -> None:
    out = SignRenderer(converter=HamNoSysToSigML(use_external=False)).render(_surface())
    assert out.valid
    assert out.payload["gloss"] == "manu"
    assert out.payload["avatar_ok"] is True


def test_renderer_with_explicit_annotation() -> None:
    out = SignRenderer(converter=HamNoSysToSigML(use_external=False)).render(
        _surface(), hamnosys="sym:hamfinger2 sym:hamchest sym:hammoveo"
    )
    assert out.valid
    assert "hns_sign" in out.payload["sigml"]


def test_all_allowed_symbols_are_valid() -> None:
    for sym in sorted(ALLOWED_SYMBOLS):
        xml = HamNoSysToSigML(use_external=False).convert(f"sym:{sym}")
        ok, errors = validate_sigml(xml)
        assert ok, (sym, errors)
