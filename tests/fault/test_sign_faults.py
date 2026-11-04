"""Sign fault injection: OOD input must fall back to procedural Animgen."""

from __future__ import annotations

from oarumi.reliability.symbolic_shield import ParityContract
from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer, validate_sigml
from oarumi.types import Clitic, OarumiSurface, ValidationOutcome


def _surface() -> OarumiSurface:
    return OarumiSurface(
        phonemes=("manu",),
        clitics=(Clitic("=ha", "mood_declarative"),),
        mood="DECL",
        modality="signed",
    )


def test_ood_annotation_falls_back(shield) -> None:
    procedural = SignRenderer(converter=HamNoSysToSigML(use_external=False))

    def neural_ood(surface: OarumiSurface):
        # Simulate a diffusion model that emits invalid XML for OOD input.
        return procedural.render(surface, hamnosys="sym:not_real")

    def validator(out) -> ValidationOutcome:
        return ValidationOutcome(valid=out.valid, errors=out.errors)

    call = shield.wrap(
        component="sign",
        neural=neural_ood,
        validator=validator,
        fallback=lambda s: procedural.render(s),
        contract=ParityContract(validity_required=True),
    )
    r = call(_surface())
    assert r.decision == "use_fallback"
    assert r.output is not None
    ok, _ = validate_sigml(r.output.payload["sigml"])
    assert ok
