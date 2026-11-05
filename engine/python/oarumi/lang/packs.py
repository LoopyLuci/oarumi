"""Language packs: the index, integrity checks, and on-device storage.

A pack is one JSON file per language (see tools/build_language_packs.py).
Base packs ship with every build under `bundled_dir`. Extra packs are copied
into `installed_dir` after a download, and that copy is used in preference.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class PackError(Exception):
    """A pack is missing, malformed, or fails its checksum."""


@dataclass(frozen=True, slots=True)
class PackEntry:
    code: str
    name: str
    base: bool
    spell: bool
    detect: bool
    file: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class LanguagePack:
    code: str
    name: str
    base: bool
    words: dict[str, int]
    ngrams: dict[str, int]


def parse_index(raw: bytes) -> tuple[PackEntry, ...]:
    data = json.loads(raw.decode("utf-8"))
    entries: list[PackEntry] = []
    for item in data["packs"]:
        entries.append(
            PackEntry(
                code=str(item["code"]),
                name=str(item["name"]),
                base=bool(item["base"]),
                spell=bool(item["spell"]),
                detect=bool(item["detect"]),
                file=str(item["file"]),
                size_bytes=int(item["size_bytes"]),
                sha256=str(item["sha256"]),
            )
        )
    return tuple(entries)


def verify(blob: bytes, entry: PackEntry) -> None:
    """Raise PackError unless `blob` matches the size and SHA-256 in `entry`."""
    if len(blob) != entry.size_bytes:
        raise PackError(f"{entry.code}: size {len(blob)} does not match index {entry.size_bytes}")
    digest = hashlib.sha256(blob).hexdigest()
    if digest != entry.sha256:
        raise PackError(f"{entry.code}: checksum mismatch")


def parse_pack(raw: bytes) -> LanguagePack:
    data = json.loads(raw.decode("utf-8"))
    return LanguagePack(
        code=str(data["code"]),
        name=str(data["name"]),
        base=bool(data["base"]),
        words={str(word): int(count) for word, count in data["words"]},
        ngrams={str(gram): int(count) for gram, count in data["ngrams"].items()},
    )


class PackStore:
    """Finds, loads and removes packs on this device."""

    def __init__(self, bundled_dir: Path, installed_dir: Path) -> None:
        self._bundled = bundled_dir
        self._installed = installed_dir

    def bundled_index(self) -> tuple[PackEntry, ...]:
        return parse_index((self._bundled / "index.json").read_bytes())

    def path_for(self, entry: PackEntry) -> Path | None:
        """Installed copy if present, else the bundled copy for base packs."""
        installed = self._installed / entry.file
        if installed.exists():
            return installed
        bundled = self._bundled / entry.file
        if entry.base and bundled.exists():
            return bundled
        return None

    def is_installed(self, entry: PackEntry) -> bool:
        return self.path_for(entry) is not None

    def load(self, code: str) -> LanguagePack:
        entry = self._entry(code)
        path = self.path_for(entry)
        if path is None:
            raise PackError(f"{code}: pack is not installed")
        return parse_pack(path.read_bytes())

    def store(self, entry: PackEntry, blob: bytes) -> Path:
        """Verify `blob` against the index and write it atomically."""
        verify(blob, entry)
        self._installed.mkdir(parents=True, exist_ok=True)
        target = self._installed / entry.file
        partial = target.with_suffix(".partial")
        partial.write_bytes(blob)
        partial.replace(target)
        return target

    def remove(self, entry: PackEntry) -> None:
        """Delete the installed copy. Bundled base packs cannot be removed."""
        installed = self._installed / entry.file
        if installed.exists():
            installed.unlink()

    def _entry(self, code: str) -> PackEntry:
        for entry in self.bundled_index():
            if entry.code == code:
                return entry
        raise PackError(f"{code}: unknown pack")
