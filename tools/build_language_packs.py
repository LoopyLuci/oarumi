"""Build the language packs under language/packs/ from upstream word and profile data.

Two upstream sources feed each pack:

* Word frequencies from the ``pyspellchecker`` wheel (MIT). They become the
  spelling dictionary and the suggestion vocabulary.
* Character n-gram profiles from the ``langdetect`` sdist (Apache-2.0). They
  become the detection model. Profile keys are lowercased and merged so the
  detector only has to normalise its input once.

Usage (download the two upstream artifacts first, then point at them):

    pip download pyspellchecker==0.8.1 --no-deps -d downloads
    pip download langdetect==1.0.9 --no-deps --no-binary :all: -d downloads
    python -m tools.build_language_packs \\
        --spell-wheel downloads/pyspellchecker-0.8.1-py3-none-any.whl \\
        --profiles-sdist downloads/langdetect-1.0.9.tar.gz

The output is deterministic: sorted keys, LF endings, fixed separators. The
index records the SHA-256 of every pack file so a device can verify a download.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_TOP_WORDS = 30_000
REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ROOT = REPO_ROOT / "engine" / "python"
DEFAULT_OUT = REPO_ROOT / "language" / "packs"


@dataclass(frozen=True, slots=True)
class PackSpec:
    code: str
    name: str
    base: bool
    spell_resource: str | None
    profile: str


# Base packs ship inside every app build. Extra packs are stored in the repo
# and downloaded on demand from the index.
PACK_SPECS: tuple[PackSpec, ...] = (
    PackSpec("en", "English", True, "en", "en"),
    PackSpec("es", "Spanish", True, "es", "es"),
    PackSpec("fr", "French", True, "fr", "fr"),
    PackSpec("de", "German", True, "de", "de"),
    PackSpec("zh", "Mandarin Chinese", True, None, "zh-cn"),
    PackSpec("ar", "Arabic", True, "ar", "ar"),
    PackSpec("pt", "Portuguese", False, "pt", "pt"),
    PackSpec("it", "Italian", False, "it", "it"),
    PackSpec("nl", "Dutch", False, "nl", "nl"),
    PackSpec("ru", "Russian", False, "ru", "ru"),
    PackSpec("lv", "Latvian", False, "lv", "lv"),
    PackSpec("tr", "Turkish", False, None, "tr"),
    PackSpec("pl", "Polish", False, None, "pl"),
    PackSpec("sv", "Swedish", False, None, "sv"),
    PackSpec("hi", "Hindi", False, None, "hi"),
    PackSpec("ja", "Japanese", False, None, "ja"),
    PackSpec("ko", "Korean", False, None, "ko"),
    PackSpec("th", "Thai", False, None, "th"),
)


def load_word_frequencies(wheel: Path, resource: str, top: int) -> list[tuple[str, int]]:
    with zipfile.ZipFile(wheel) as archive:
        raw = gzip.decompress(archive.read(f"spellchecker/resources/{resource}.json.gz"))
    counts: dict[str, int] = json.loads(raw.decode("utf-8"))
    words = [(word, int(count)) for word, count in counts.items() if word.isalpha()]
    words.sort(key=lambda item: (-item[1], item[0]))
    return words[:top]


def phrasebook_words(code: str) -> list[str]:
    """Words from the seed phrasebook for `code`, so common phrases are never flagged."""
    sys.path.insert(0, str(ENGINE_ROOT))
    try:
        from oarumi.lang.text import split_words
        from oarumi.pivot import phrasebook
    finally:
        sys.path.remove(str(ENGINE_ROOT))
    words: list[str] = []
    for phrase in phrasebook.phrases(code):
        words.extend(word.text for word in split_words(phrase))
    return words


def merge_phrasebook(words: list[tuple[str, int]], code: str) -> list[list[object]]:
    counts: dict[str, int] = dict(words)
    for word in phrasebook_words(code):
        counts[word] = max(counts.get(word, 0), 1)
    merged = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [[word, count] for word, count in merged]


def load_ngram_profile(sdist: Path, profile: str) -> dict[str, int]:
    member_name = f"langdetect-{_sdist_version(sdist)}/langdetect/profiles/{profile}"
    with tarfile.open(sdist, "r:gz") as archive:
        member = archive.extractfile(member_name)
        if member is None:
            raise FileNotFoundError(f"profile {profile!r} not found in {sdist}")
        data = json.loads(member.read().decode("utf-8"))
    merged: dict[str, int] = {}
    for gram, count in data["freq"].items():
        key = gram.lower()
        merged[key] = merged.get(key, 0) + int(count)
    return dict(sorted(merged.items()))


def _sdist_version(sdist: Path) -> str:
    stem = sdist.name
    if stem.endswith(".tar.gz"):
        stem = stem[: -len(".tar.gz")]
    return stem.rsplit("-", 1)[1]


def build_pack(
    spec: PackSpec, spell_wheel: Path, profiles_sdist: Path, top: int
) -> dict[str, object]:
    words: list[list[object]] = []
    if spec.spell_resource is not None:
        words = merge_phrasebook(
            load_word_frequencies(spell_wheel, spec.spell_resource, top), spec.code
        )
    ngrams = load_ngram_profile(profiles_sdist, spec.profile)
    return {
        "schema": SCHEMA_VERSION,
        "code": spec.code,
        "name": spec.name,
        "base": spec.base,
        "spell": spec.spell_resource is not None,
        "detect": True,
        "sources": {
            "words": (
                f"pyspellchecker wheel (MIT) resource {spec.spell_resource}"
                if spec.spell_resource
                else None
            ),
            "ngrams": f"langdetect sdist (Apache-2.0) profile {spec.profile}",
        },
        "words": words,
        "ngrams": ngrams,
    }


def serialise(pack: dict[str, object]) -> bytes:
    text = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def build_all(
    spell_wheel: Path, profiles_sdist: Path, out_dir: Path, top: int
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for spec in PACK_SPECS:
        blob = serialise(build_pack(spec, spell_wheel, profiles_sdist, top))
        file_name = f"{spec.code}.json"
        (out_dir / file_name).write_bytes(blob)
        entries.append(
            {
                "code": spec.code,
                "name": spec.name,
                "base": spec.base,
                "spell": spec.spell_resource is not None,
                "detect": True,
                "file": file_name,
                "size_bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
    index: dict[str, object] = {"schema": SCHEMA_VERSION, "packs": entries}
    (out_dir / "index.json").write_bytes(serialise(index))
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--spell-wheel", type=Path, required=True)
    parser.add_argument("--profiles-sdist", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_WORDS)
    args = parser.parse_args()
    index = build_all(args.spell_wheel, args.profiles_sdist, args.out, args.top)
    packs = index["packs"]
    assert isinstance(packs, list)
    print(f"wrote {len(packs)} packs to {args.out}")


if __name__ == "__main__":
    main()
