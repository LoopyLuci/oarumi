"""Desktop language packs: list, download, verify, remove, and serve spelling and detection.

The index comes from the repo copy of language/packs/index.json, which is also
what the app was built with. A download is accepted only if its size and
SHA-256 match that index. Installed packs live under OARUMI_HOME/packs, or
~/.oarumi/packs when OARUMI_HOME is unset.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from oarumi.lang import LanguageDetector, PackEntry, PackStore, SpellChecker

PACK_BASE_URL = "https://raw.githubusercontent.com/LoopyLuci/oarumi/main/language/packs/"
REPO_PACKS = Path(__file__).resolve().parents[1] / "language" / "packs"
DOWNLOAD_TIMEOUT_SECONDS = 30


def installed_packs_dir() -> Path:
    home = os.environ.get("OARUMI_HOME")
    base = Path(home) if home else Path.home() / ".oarumi"
    return base / "packs"


class PackManager:
    def __init__(
        self,
        bundled_dir: Path = REPO_PACKS,
        installed_dir: Path | None = None,
    ) -> None:
        self.store = PackStore(bundled_dir, installed_dir or installed_packs_dir())
        self._detector: LanguageDetector | None = None
        self._spellers: dict[str, SpellChecker] = {}

    def entries(self) -> tuple[PackEntry, ...]:
        return self.store.bundled_index()

    def is_installed(self, entry: PackEntry) -> bool:
        return self.store.is_installed(entry)

    def download(self, entry: PackEntry) -> None:
        url = PACK_BASE_URL + entry.file
        request = urllib.request.Request(url, headers={"User-Agent": "oarumi-desktop"})
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            blob = response.read()
        self.store.store(entry, blob)
        self.invalidate()

    def remove(self, entry: PackEntry) -> None:
        self.store.remove(entry)
        self.invalidate()

    def invalidate(self) -> None:
        self._detector = None
        self._spellers.clear()

    def detector(self) -> LanguageDetector:
        if self._detector is None:
            profiles: dict[str, dict[str, int]] = {}
            dictionaries: dict[str, dict[str, int]] = {}
            for entry in self.entries():
                if not self.is_installed(entry):
                    continue
                pack = self.store.load(entry.code)
                profiles[entry.code] = pack.ngrams
                if pack.words:
                    dictionaries[entry.code] = pack.words
            self._detector = LanguageDetector(profiles, dictionaries)
        return self._detector

    def spell_checker(self, code: str) -> SpellChecker | None:
        """The spelling dictionary for `code`, or None when no installed pack has one."""
        if code not in self._spellers:
            entry = next((e for e in self.entries() if e.code == code), None)
            if entry is None or not entry.spell or not self.is_installed(entry):
                return None
            self._spellers[code] = SpellChecker.from_pack(self.store.load(code))
        return self._spellers[code]
