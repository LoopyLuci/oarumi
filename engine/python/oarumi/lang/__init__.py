"""On-device language packs, spell checking, and language detection."""

from oarumi.lang.detect import MIN_MARGIN, Detection, LanguageDetector
from oarumi.lang.packs import LanguagePack, PackEntry, PackError, PackStore
from oarumi.lang.spell import Misspelling, SpellChecker

__all__ = [
    "MIN_MARGIN",
    "Detection",
    "LanguageDetector",
    "LanguagePack",
    "Misspelling",
    "PackEntry",
    "PackError",
    "PackStore",
    "SpellChecker",
]
