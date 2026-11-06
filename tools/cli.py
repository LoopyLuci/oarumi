"""Oarumi command-line interface.

Subcommands:

    translate   full pipeline (source language -> Oarumi, or Oarumi -> source)
    decompose   pivot text -> NSMStructure JSON
    realize     NSMStructure JSON -> OarumiSurface JSON
    render      OarumiSurface JSON -> a modality payload (spoken/signed/tactile)
    route       show the intent-router decision for a request (debug)
    validate    run every schema + prime validator
    audio       generate or verify the click/hum audio assets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from oarumi.config import EngineConfig
from oarumi.db import LanguageDb
from oarumi.pipeline import Pipeline

from tools import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "language" / "oarumi.db"


# --- lazily-constructed shared objects ---------------------------------


class _Context:
    def __init__(self) -> None:
        self._db: LanguageDb | None = None
        self._pipeline: Pipeline | None = None
        self._cfg: EngineConfig | None = None

    @property
    def cfg(self) -> EngineConfig:
        if self._cfg is None:
            self._cfg = EngineConfig.from_env()
        return self._cfg

    @property
    def db(self) -> LanguageDb:
        if self._db is None:
            if not DB_PATH.exists():
                raise SystemExit(f"language DB not found at {DB_PATH}; run ./scripts/bootstrap.sh")
            self._db = LanguageDb(DB_PATH)
        return self._db

    @property
    def pipeline(self) -> Pipeline:
        if self._pipeline is None:
            self._pipeline = Pipeline(db=self.db, cfg=self.cfg)
        return self._pipeline

    def close(self) -> None:
        if self._db is not None:
            self._db.close()


# --- command implementations -------------------------------------------


def _cmd_translate(args: argparse.Namespace, ctx: _Context) -> int:
    from oarumi.types import TranslationRequest

    text: str = args.text
    from_lang: str = args.from_lang
    to_lang: str = args.to

    # Routing.
    if to_lang.lower() not in {"oarumi", "oar"}:
        print(
            f"error: only '--to oarumi' is supported by the full pipeline today; "
            f"got {to_lang!r}. (other-to-other is on the roadmap)",
            file=sys.stderr,
        )
        return 2

    req = TranslationRequest(
        text=text,
        lang=from_lang,
        modality=args.modality,
        target_modality=args.target_modality,
    )
    result = ctx.pipeline.translate(req)
    payload = result.to_json()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"input:       {text!r} ({from_lang})")
    print(f"pivot:       {result.pivot['text']!r} ({result.pivot['source']})")
    print(f"surface:     {result.surface.to_string()}")
    print(f"mood:        {result.surface.mood}")
    print(f"degraded:    {result.degraded}")
    for ev in result.failover_events:
        print(f"failover:    {ev.get('component')}: {ev.get('trigger')}")
    return 0


def _cmd_decompose(args: argparse.Namespace, ctx: _Context) -> int:
    from oarumi.errors import ValidationError
    from oarumi.nsm.decomposer import NSMDecomposerTierA

    dec = NSMDecomposerTierA(ctx.db)
    try:
        nsm = dec.decompose(args.text)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        for e in exc.errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    payload = nsm.to_json()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for c in nsm.combinators:
            print(f"{c.head}({', '.join(c.args)})")
    return 0


def _cmd_realize(args: argparse.Namespace, ctx: _Context) -> int:
    from oarumi.errors import ValidationError
    from oarumi.nsm.realizer import NSMRealizer
    from oarumi.types import NSMStructure

    try:
        nsm = NSMStructure.from_json(json.loads(args.nsm_json))
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"error: bad NSM JSON: {exc}", file=sys.stderr)
        return 2

    try:
        surface = NSMRealizer(ctx.db).realize(nsm, modality=args.modality)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(surface.to_json(), ensure_ascii=False, indent=2))
    return 0


def _cmd_render(args: argparse.Namespace, ctx: _Context) -> int:
    from oarumi.types import OarumiSurface

    try:
        surface = OarumiSurface.from_json(json.loads(args.surface_json))
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"error: bad surface JSON: {exc}", file=sys.stderr)
        return 2

    if args.modality == "spoken":
        from oarumi.renderers.audio_assets import AudioAssetLibrary
        from oarumi.renderers.tts import TtsRenderer

        audio = AudioAssetLibrary(REPO_ROOT / "assets" / "audio", require_verified=False)
        out = TtsRenderer(audio=audio).render(surface)
    elif args.modality == "signed":
        from oarumi.renderers.sign import HamNoSysToSigML, SignRenderer

        out = SignRenderer(converter=HamNoSysToSigML(use_external=False)).render(surface)
    elif args.modality == "tactile":
        from oarumi.renderers.tactile import TactileRenderer

        out = TactileRenderer().render(surface)
    else:
        print(f"error: unknown modality {args.modality!r}", file=sys.stderr)
        return 2

    print(json.dumps(out.to_json(), ensure_ascii=False, indent=2))
    return 0 if out.valid else 1


def _cmd_route(args: argparse.Namespace, ctx: _Context) -> int:
    from oarumi.reliability.intent_router import IntentRouter, StaticCapabilitySource
    from oarumi.types import TranslationRequest

    router = IntentRouter(source=StaticCapabilitySource(db=ctx.db, offline=ctx.cfg.offline))
    req = TranslationRequest(text=args.text, lang=args.lang)
    route = router.route(req)
    print(json.dumps(route.to_json(), indent=2))
    return 0


def _cmd_validate(_: argparse.Namespace, __: _Context) -> int:
    from tools import validate_primes, validate_schemas

    rc1 = validate_schemas.main(["--all"])
    rc2 = validate_primes.main([])
    return 0 if rc1 == 0 and rc2 == 0 else 1


def _cmd_audio(args: argparse.Namespace, ctx: _Context) -> int:
    del ctx
    if args.audio_cmd == "generate":
        from tools import generate_audio_assets

        argv = ["--dest", str(REPO_ROOT / "assets" / "audio")]
        return generate_audio_assets.main(argv)
    if args.audio_cmd == "verify":
        from oarumi.errors import IntegrityError
        from oarumi.renderers.audio_assets import AudioAssetLibrary

        try:
            lib = AudioAssetLibrary(REPO_ROOT / "assets" / "audio", require_verified=True)
        except (IntegrityError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"OK   {len(lib.ids())} audio assets verified")
        return 0
    print(f"error: unknown audio subcommand {args.audio_cmd!r}", file=sys.stderr)
    return 2


# --- argument parsing ---------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oarumi", description=__doc__)
    parser.add_argument("--version", action="version", version=f"oarumi {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("translate", help="Run the full pipeline")
    p.add_argument("text", help="Input text")
    p.add_argument("--from", dest="from_lang", required=True, help="Source language code")
    p.add_argument("--to", dest="to", default="oarumi", help="Target language code")
    p.add_argument("--modality", default="spoken", choices=["spoken", "signed", "tactile", "text"])
    p.add_argument(
        "--target-modality", default=None, choices=["spoken", "signed", "tactile", "text"]
    )
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.set_defaults(func=_cmd_translate)

    p = sub.add_parser("decompose", help="Pivot text -> NSMStructure")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_decompose)

    p = sub.add_parser("realize", help="NSMStructure JSON -> OarumiSurface JSON")
    p.add_argument("nsm_json", help="NSM JSON string")
    p.add_argument("--modality", default="spoken", choices=["spoken", "signed", "tactile", "text"])
    p.set_defaults(func=_cmd_realize)

    p = sub.add_parser("render", help="OarumiSurface JSON -> modality payload")
    p.add_argument("surface_json", help="Surface JSON string")
    p.add_argument("--modality", required=True, choices=["spoken", "signed", "tactile"])
    p.set_defaults(func=_cmd_render)

    p = sub.add_parser("route", help="Show intent-router decision (debug)")
    p.add_argument("text")
    p.add_argument("--lang", required=True)
    p.set_defaults(func=_cmd_route)

    p = sub.add_parser("validate", help="Run schema + prime validators")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("audio", help="Audio asset operations")
    audio_sub = p.add_subparsers(dest="audio_cmd", required=True)
    audio_sub.add_parser("generate", help="Regenerate click/hum WAVs + manifest")
    audio_sub.add_parser("verify", help="Verify manifest hashes")
    p.set_defaults(func=_cmd_audio)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    ctx = _Context()
    try:
        rc: int = args.func(args, ctx)
    except KeyboardInterrupt:
        return 130
    finally:
        ctx.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
