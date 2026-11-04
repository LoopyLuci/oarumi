"""Validate every YAML file under language/ against its JSON Schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / "language"
SCHEMAS = LANG / "schemas"

# YAML file stem -> schema file stem.
PAIRS = {
    "primes": "primes.schema.json",
    "phonology": "phonology.schema.json",
    "morphology": "morphology.schema.json",
    "syntax": "syntax.schema.json",
    "prosody": "prosody.schema.json",
    "signs/classifiers": "classifiers.schema.json",
    "tactile/protactile": "protactile.schema.json",
}


def validate_one(rel: str, schema_name: str) -> list[str]:
    yaml_path = LANG / f"{rel}.yaml"
    schema_path = SCHEMAS / schema_name
    errors: list[str] = []

    if not yaml_path.exists():
        return [f"missing YAML: {yaml_path}"]
    if not schema_path.exists():
        return [f"missing schema: {schema_path}"]

    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    with schema_path.open(encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)

    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{yaml_path}:{loc}: {err.message}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="validate every file")
    parser.add_argument("--only", help="validate a single YAML stem")
    args = parser.parse_args(argv)

    if not args.all and not args.only:
        parser.error("pass --all or --only <stem>")

    pairs = PAIRS if args.all else {args.only: PAIRS[args.only]}
    failures: list[str] = []
    for rel, schema_name in pairs.items():
        failures.extend(validate_one(rel, schema_name))

    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1

    print(f"OK   validated {len(pairs)} YAML file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
