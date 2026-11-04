"""Freeze renderer parity gold from the Python implementation. Idempotent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "parity" / "data" / "renderers"


def _write(path: Path, text: str) -> None:
    # Explicit UTF-8: gold contains IPA/click glyphs that the Windows default codepage cannot encode.
    path.write_text(text, encoding="utf-8")


def freeze_tts() -> int:
    from oarumi.renderers.audio_assets import AudioAssetLibrary
    from oarumi.renderers.tts import TtsRenderer
    from oarumi.types import Clitic, OarumiSurface

    assets = AudioAssetLibrary(ROOT / "assets" / "audio", require_verified=False)
    renderer = TtsRenderer(audio=assets, espeak_bin=None)
    renderer.espeak_bin = None  # force asset backend for determinism

    cases = json.loads((FIXTURES / "tts" / "cases.json").read_text(encoding="utf-8"))
    (FIXTURES / "tts" / "gold").mkdir(exist_ok=True)

    for case in cases["cases"]:
        surf = case["surface"]
        surface = OarumiSurface(
            phonemes=tuple(surf["phonemes"]),
            clitics=tuple(Clitic(c["form"], c["type"]) for c in surf["clitics"]),
            mood=surf["mood"],
            modality=surf["modality"],
        )
        out = renderer.render(surface).to_json()
        out.pop("audio_path", None)
        out.pop("duration_ms", None)
        if out.get("backend") in ("espeak", "android", "native"):
            out["backend"] = "native"
        _write(
            FIXTURES / "tts" / "gold" / f"{case['id']}.json",
            json.dumps(out, indent=2, ensure_ascii=False) + "\n",
        )
    return len(cases["cases"])


def freeze_sign() -> int:
    from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer
    from oarumi.types import Clitic, OarumiSurface

    renderer = SignRenderer(converter=HamNoSysToSigML(use_external=False))
    cases = json.loads((FIXTURES / "sign" / "cases.json").read_text(encoding="utf-8"))
    (FIXTURES / "sign" / "gold").mkdir(exist_ok=True)

    for case in cases["cases"]:
        gloss = case["gloss"]
        annot = case["annotation"]
        surface = OarumiSurface(
            phonemes=(gloss,),
            clitics=(Clitic("=ha", "mood_declarative"),),
            mood="DECL",
            modality="signed",
        )
        out = renderer.render(surface, hamnosys=annot, gloss=gloss).to_json()
        _write(
            FIXTURES / "sign" / "gold" / f"{case['id']}.json",
            json.dumps(out, indent=2, ensure_ascii=False) + "\n",
        )
    return len(cases["cases"])


def freeze_tactile() -> int:
    from oarumi.renderers.tactile import TactileRenderer
    from oarumi.types import Clitic, OarumiSurface

    renderer = TactileRenderer()
    cases = json.loads((FIXTURES / "tactile" / "cases.json").read_text(encoding="utf-8"))
    (FIXTURES / "tactile" / "gold").mkdir(exist_ok=True)

    for case in cases["cases"]:
        surf = case["surface"]
        surface = OarumiSurface(
            phonemes=tuple(surf["phonemes"]),
            clitics=tuple(Clitic(c["form"], c["type"]) for c in surf["clitics"]),
            mood=surf["mood"],
            modality=surf["modality"],
        )
        out = renderer.render(surface).to_json()
        _write(
            FIXTURES / "tactile" / "gold" / f"{case['id']}.json",
            json.dumps(out, indent=2, ensure_ascii=False) + "\n",
        )
    return len(cases["cases"])


def main() -> int:
    tts_n = freeze_tts()
    sign_n = freeze_sign()
    tactile_n = freeze_tactile()
    print(f"OK   froze tts={tts_n} sign={sign_n} tactile={tactile_n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
