"""Sign parity: byte-identical SiGML across runs and languages."""

from __future__ import annotations

from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer, validate_sigml
from oarumi.types import Clitic, OarumiSurface


def test_sigml_bytes_are_stable() -> None:
    r = SignRenderer(converter=HamNoSysToSigML(use_external=False))
    surface = OarumiSurface(
        phonemes=("manu",),
        clitics=(Clitic("=ha", "mood_declarative"),),
        mood="DECL",
        modality="signed",
    )
    out1 = r.render(surface)
    out2 = r.render(surface)
    assert out1.payload["sigml"] == out2.payload["sigml"]


def test_all_valid_symbols_produce_valid_sigml() -> None:
    from oarumi.renderers.sign import ALLOWED_SYMBOLS

    conv = HamNoSysToSigML(use_external=False)
    for sym in ALLOWED_SYMBOLS:
        xml = conv.convert(f"sym:{sym}", gloss="test")
        ok, errors = validate_sigml(xml)
        assert ok, f"{sym}: {errors}"


def test_unknown_symbol_marks_invalid() -> None:
    conv = HamNoSysToSigML(use_external=False)
    xml = conv.convert("sym:hamnotarealsymbol", gloss="test")
    ok, errors = validate_sigml(xml)
    assert not ok
    assert any("unknown_symbol" in e for e in errors)


def test_pipeline_signed_modality_present(engine_pipeline) -> None:
    from oarumi.types import TranslationRequest

    result = engine_pipeline.translate(
        TranslationRequest(text="hola", lang="es", modality="signed")
    )
    assert "signed" in result.modalities
    assert "sigml" in result.modalities["signed"]
    assert result.modalities["signed"]["sigml"].startswith("<sigml")
