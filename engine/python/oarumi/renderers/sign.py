"""Signed renderer: HamNoSys annotation -> SiGML XML.

The converter has two paths:
  1. The `hamnosys` PyPI package, if importable (fast, maintained).
  2. A built-in symbol map, which covers the subset of HamNoSys used by the
     seed corpus and is deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from oarumi.renderers.base import RenderOutput
from oarumi.types import OarumiSurface

SIGML_NS = "https://vhg.cmp.uea.ac.uk/tech/jas/sigml"
SIGML_ROOT = "sigml"
HNS_SIGN = "hns_sign"
MANUAL = "hamnosys_manual"

# Whitelist of HamNoSys symbol names the built-in converter accepts.
ALLOWED_SYMBOLS: frozenset[str] = frozenset(
    {
        "hamfinger2",
        "hamthumbout",
        "hamnohandchange",
        "hamarcsym",
        "hamextfingeru",
        "hamextfingerd",
        "hamextfingerl",
        "hamextfingerr",
        "hampalmd",
        "hampalmr",
        "hampalmup",
        "hampalmdown",
        "hamshoulders",
        "hamchest",
        "hamwaist",
        "hamhead",
        "hammoveo",
        "hammoveu",
        "hammoved",
        "hammovel",
        "hammover",
        "hamrepeat",
        "hamplus",
        "hamsmallmod",
        "hamlargemod",
        "hamtouch",
        "hamcircle",
        "hamstraight",
    }
)

TOKEN_RE = re.compile(r"^(?:sym:)?(?P<name>ham[a-z0-9_]+)$")


@dataclass(slots=True)
class HamNoSysToSigML:
    """Convert a whitespace-separated token stream to a SiGML document."""

    use_external: bool = True

    def convert(self, annotation: str, gloss: str = "") -> str:
        if self.use_external:
            external = self._try_external(annotation, gloss)
            if external is not None:
                return external
        return self._builtin(annotation, gloss)

    def _try_external(self, annotation: str, gloss: str) -> str | None:
        try:
            from hamnosys import HamToSigml  # type: ignore[import-not-found]
        except ImportError:
            return None
        try:
            converter = HamToSigml()
            return str(converter.convert(annotation, gloss=gloss))
        except Exception:
            return None

    def _builtin(self, annotation: str, gloss: str) -> str:
        root = ET.Element(SIGML_ROOT, {"xmlns": SIGML_NS})
        sign = ET.SubElement(root, HNS_SIGN, {"gloss": gloss or "UNKNOWN"})
        manual = ET.SubElement(sign, MANUAL)
        for raw in annotation.split():
            m = TOKEN_RE.match(raw.strip())
            if m is None:
                ET.SubElement(manual, "hamunknown", {"sym": raw.strip()})
                continue
            name = m.group("name")
            if name not in ALLOWED_SYMBOLS:
                ET.SubElement(manual, "hamunknown", {"sym": name})
                continue
            ET.SubElement(manual, name)
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")


def _local(tag: str) -> str:
    """Strip the XML namespace: ElementTree reports ``{ns}name`` for default-namespaced docs."""
    return tag.rsplit("}", 1)[-1]


def validate_sigml(xml: str) -> tuple[bool, tuple[str, ...]]:
    """Structural validator used by tests and by the symbolic shield."""
    errors: list[str] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        return False, (f"parse_error:{exc}",)
    if _local(root.tag) != SIGML_ROOT:
        errors.append(f"root:{root.tag}")
    signs = [el for el in root if _local(el.tag) == HNS_SIGN]
    if len(signs) != 1:
        errors.append(f"hns_sign_count:{len(signs)}")
        return (not errors), tuple(errors)
    sign = signs[0]
    if "gloss" not in sign.attrib:
        errors.append("hns_sign:missing_gloss")
    manual = next((el for el in sign if _local(el.tag) == MANUAL), None)
    if manual is None:
        errors.append("hamnosys_manual:missing")
        return (not errors), tuple(errors)
    for child in manual:
        name = _local(child.tag)
        if name == "hamunknown":
            errors.append(f"unknown_symbol:{child.attrib.get('sym', '')}")
        elif name not in ALLOWED_SYMBOLS:
            errors.append(f"unexpected_element:{name}")
    return (not errors), tuple(errors)


@dataclass(slots=True)
class SignRenderer:
    converter: HamNoSysToSigML = None  # type: ignore[assignment]
    modality: str = "signed"

    def __post_init__(self) -> None:
        if self.converter is None:
            self.converter = HamNoSysToSigML()

    def render(
        self,
        surface: OarumiSurface,
        *,
        hamnosys: str | None = None,
        gloss: str | None = None,
        **kwargs: Any,
    ) -> RenderOutput:
        annotation = hamnosys
        if annotation is None:
            annotation = (
                "sym:hamfinger2 sym:hamthumbout sym:hamnohandchange "
                "sym:hamarcsym sym:hamextfingeru"
            )
        use_gloss = gloss or (surface.phonemes[0] if surface.phonemes else "UNKNOWN")
        xml = self.converter.convert(annotation, gloss=use_gloss)
        ok, errors = validate_sigml(xml)
        return RenderOutput(
            modality=self.modality,
            payload={"sigml": xml, "avatar_ok": ok, "gloss": use_gloss},
            valid=ok,
            errors=errors,
        )
