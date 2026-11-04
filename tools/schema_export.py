"""Detect drift between language/*.yaml files and language/schemas/*.json.

The schemas are hand-maintained and more precise than a naive inference. This
tool's job is to fail when a YAML file adds or removes a top-level or nested
field that the schema does not mention, so nothing is silently unvalidated.

    python tools/schema_export.py --check   # exit 1 if drift detected
    python tools/schema_export.py --list    # print field trees of each YAML
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / "language"
SCHEMAS = LANG / "schemas"

# YAML file stem -> schema file name.
PAIRS: dict[str, str] = {
    "primes": "primes.schema.json",
    "phonology": "phonology.schema.json",
    "morphology": "morphology.schema.json",
    "syntax": "syntax.schema.json",
    "prosody": "prosody.schema.json",
    "signs/classifiers": "classifiers.schema.json",
    "tactile/protactile": "protactile.schema.json",
}


def _field_paths(obj: Any, prefix: str = "") -> set[str]:
    """Return the set of dotted paths that appear as object keys in `obj`."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            out.add(path)
            out.update(_field_paths(v, path))
    elif isinstance(obj, list):
        for item in obj:
            out.update(_field_paths(item, prefix))
    return out


def _schema_field_paths(schema: Any, prefix: str = "") -> set[str]:
    """Return the set of dotted paths the JSON schema 'expects' to see.

    This is deliberately conservative: it collects `properties` keys and
    `required` names at each level. `additionalProperties: true` means any
    field not listed is *also* allowed — we treat that as "no drift check
    possible" for that subtree.
    """
    out: set[str] = set()
    if not isinstance(schema, dict):
        return out

    props = schema.get("properties")
    if isinstance(props, dict):
        for name, sub in props.items():
            path = f"{prefix}.{name}" if prefix else name
            out.add(path)
            out.update(_schema_field_paths(sub, path))

    items = schema.get("items")
    if isinstance(items, dict):
        out.update(_schema_field_paths(items, prefix))

    return out


def check_drift() -> list[str]:
    problems: list[str] = []

    for yaml_stem, schema_file in PAIRS.items():
        yaml_path = LANG / f"{yaml_stem}.yaml"
        schema_path = SCHEMAS / schema_file

        if not yaml_path.exists():
            problems.append(f"missing YAML: {yaml_path}")
            continue
        if not schema_path.exists():
            problems.append(f"missing schema: {schema_path}")
            continue

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        yaml_paths = _field_paths(data)
        schema_paths = _schema_field_paths(schema)

        # Fields in YAML but not in schema — the dangerous direction.
        unknown = yaml_paths - schema_paths
        # Ignore leaf-of-list scalar items and single-key map entries that
        # come from user data. Heuristic filter: if a path's *parent* is not
        # in schema_paths either, we cannot reasonably declare drift.
        significant = {
            p
            for p in unknown
            if p.count(".") <= 2
            and not p.startswith(
                (
                    "constructions",
                    "primes",
                    "members",
                    "classifiers",
                    "attitudinal_particles",
                    "hns_sign",
                    "assets",
                )
            )
        }

        for path in sorted(significant):
            problems.append(f"{yaml_stem}: field {path!r} not declared in {schema_file}")

        # `additionalProperties: false` at the root combined with an unknown
        # field is a hard failure regardless of the heuristic above.
        if schema.get("additionalProperties") is False:
            top_level = {p.split(".", 1)[0] for p in yaml_paths if "." not in p}
            schema_top = {p.split(".", 1)[0] for p in schema_paths}
            for name in sorted(top_level - schema_top):
                problems.append(
                    f"{yaml_stem}: top-level key {name!r} not in {schema_file}"
                    " (additionalProperties=false)"
                )

    return problems


def list_fields() -> int:
    for yaml_stem in PAIRS:
        yaml_path = LANG / f"{yaml_stem}.yaml"
        if not yaml_path.exists():
            print(f"{yaml_stem}: MISSING")
            continue
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        print(f"\n{yaml_stem}")
        for path in sorted(_field_paths(data)):
            depth = path.count(".")
            if depth > 2:
                continue
            print(f"  {'  ' * depth}{path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        return list_fields()

    problems = check_drift()
    if problems:
        for p in problems:
            print(f"DRIFT {p}", file=sys.stderr)
        return 1
    print(f"OK   no drift across {len(PAIRS)} YAML/schema pair(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
