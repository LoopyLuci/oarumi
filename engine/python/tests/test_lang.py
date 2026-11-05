"""Language packs, spell checking, and language detection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from oarumi.lang import LanguageDetector, PackError, PackStore, SpellChecker
from oarumi.lang.packs import PackEntry, parse_index, verify
from oarumi.lang.text import split_words

PACKS = Path(__file__).resolve().parents[3] / "language" / "packs"


@pytest.fixture(scope="module")
def store() -> PackStore:
    return PackStore(PACKS, PACKS)


@pytest.fixture(scope="module")
def all_packs(store: PackStore) -> dict[str, object]:
    return {entry.code: store.load(entry.code) for entry in store.bundled_index()}


@pytest.fixture(scope="module")
def detector(all_packs: dict[str, object]) -> LanguageDetector:
    profiles = {code: pack.ngrams for code, pack in all_packs.items()}  # type: ignore[attr-defined]
    dictionaries = {
        code: pack.words for code, pack in all_packs.items() if pack.words  # type: ignore[attr-defined]
    }
    return LanguageDetector(profiles, dictionaries)


# --- text segmentation -------------------------------------------------------


def test_split_words_gives_spans_and_lowercases() -> None:
    words = split_words("Hola, ¿Qué tal?")
    assert [(w.start, w.end, w.text) for w in words] == [
        (0, 4, "hola"),
        (7, 10, "qué"),
        (11, 14, "tal"),
    ]


def test_split_words_keeps_combining_marks_inside_a_word() -> None:
    arabic = "مَرْحَبًا"  # vowel marks are category Mn
    assert [w.text for w in split_words(arabic)] == [arabic]


def test_digits_separate_words() -> None:
    assert [w.text for w in split_words("abc123def")] == ["abc", "def"]


# --- packs -------------------------------------------------------------------


def test_bundled_index_lists_base_packs(store: PackStore) -> None:
    base = {entry.code for entry in store.bundled_index() if entry.base}
    assert base == {"en", "es", "fr", "de", "zh", "ar"}


def test_verify_accepts_matching_blob_and_rejects_tampering() -> None:
    blob = b'{"schema":1}\n'
    entry = PackEntry(
        code="xx",
        name="Test",
        base=False,
        spell=False,
        detect=True,
        file="xx.json",
        size_bytes=len(blob),
        sha256=hashlib.sha256(blob).hexdigest(),
    )
    verify(blob, entry)
    with pytest.raises(PackError):
        verify(blob + b" ", entry)
    with pytest.raises(PackError):
        verify(b"x" * len(blob), entry)


def test_store_installs_and_removes_an_extra_pack(store: PackStore, tmp_path: Path) -> None:
    fresh = PackStore(PACKS, tmp_path)
    entry = next(e for e in fresh.bundled_index() if e.code == "pt")
    assert not fresh.is_installed(entry)
    fresh.store(entry, (PACKS / entry.file).read_bytes())
    assert fresh.is_installed(entry)
    assert fresh.load("pt").code == "pt"
    fresh.remove(entry)
    assert not fresh.is_installed(entry)


def test_store_refuses_a_blob_that_fails_its_checksum(tmp_path: Path) -> None:
    fresh = PackStore(PACKS, tmp_path)
    entry = next(e for e in fresh.bundled_index() if e.code == "pt")
    with pytest.raises(PackError):
        fresh.store(entry, b"tampered")
    assert not fresh.is_installed(entry)


def test_base_pack_cannot_be_removed_from_the_bundle(store: PackStore, tmp_path: Path) -> None:
    fresh = PackStore(PACKS, tmp_path)
    entry = next(e for e in fresh.bundled_index() if e.code == "es")
    fresh.remove(entry)  # no installed copy: nothing to delete
    assert fresh.is_installed(entry)  # bundled copy still resolves


def test_index_parser_reads_fields() -> None:
    raw = json.dumps(
        {
            "packs": [
                {
                    "code": "fr",
                    "name": "French",
                    "base": True,
                    "spell": True,
                    "detect": True,
                    "file": "fr.json",
                    "size_bytes": 3,
                    "sha256": "00",
                }
            ]
        }
    ).encode("utf-8")
    (entry,) = parse_index(raw)
    assert entry.code == "fr" and entry.size_bytes == 3 and entry.base


# --- spelling ----------------------------------------------------------------


def test_spell_suggests_the_closest_frequent_word(all_packs: dict[str, object]) -> None:
    es = SpellChecker.from_pack(all_packs["es"])  # type: ignore[arg-type]
    assert es.suggest("holla")[0] == "hola"
    assert "quiero" in es.suggest("quierro")


def test_spell_knows_phrasebook_words(all_packs: dict[str, object]) -> None:
    es = SpellChecker.from_pack(all_packs["es"])  # type: ignore[arg-type]
    assert es.is_known("gracias") and es.is_known("días") and es.is_known("quiero")


def test_spell_check_flags_only_unknown_words(all_packs: dict[str, object]) -> None:
    en = SpellChecker.from_pack(all_packs["en"])  # type: ignore[arg-type]
    problems = en.check("I recieve the wrold today 2024")
    assert [p.word for p in problems] == ["recieve", "wrold"]
    assert "receive" in problems[0].suggestions
    assert problems[1].suggestions[0] == "world"


def test_spell_gives_nothing_for_known_or_hopeless_input(all_packs: dict[str, object]) -> None:
    en = SpellChecker.from_pack(all_packs["en"])  # type: ignore[arg-type]
    assert en.suggest("hello") == ()
    assert en.suggest("zzzzzzzzzzzzzzzzzzzz") == ()


# --- detection ---------------------------------------------------------------

HELD_OUT = [
    ("¿dónde está la estación de tren?", "es"),
    ("je ne sais pas où est la gare", "fr"),
    ("ich habe heute keine Zeit", "de"),
    ("I would like a cup of coffee please", "en"),
    ("eu gostaria de um copo de água", "pt"),
    ("vorrei un bicchiere d acqua", "it"),
    ("ik wil graag een kopje koffie", "nl"),
    ("я хочу выпить чашку чая", "ru"),
    ("أين محطة القطار؟", "ar"),
    ("我想喝一杯水", "zh"),
    ("bugün çok yorgunum", "tr"),
    ("gdzie jest dworzec kolejowy", "pl"),
    ("ciao, come va?", "it"),
    ("안녕하세요 만나서 반갑습니다", "ko"),
    ("नमस्ते आप कैसे हैं", "hi"),
    ("こんにちは、お元気ですか", "ja"),
]


@pytest.mark.parametrize(("text", "expected"), HELD_OUT)
def test_detects_held_out_sentences(detector: LanguageDetector, text: str, expected: str) -> None:
    assert detector.detect(text).code == expected


def test_dictionary_bonus_settles_a_phrase(detector: LanguageDetector) -> None:
    assert detector.detect("hallo wie geht es dir").code == "de"


def test_a_word_shared_by_two_languages_stays_unsure(detector: LanguageDetector) -> None:
    # "hallo" is listed by both the German and the Dutch dictionaries.
    assert detector.detect("hallo").code is None


def test_no_letters_means_no_answer(detector: LanguageDetector) -> None:
    result = detector.detect("12345 !!")
    assert result.code is None and result.confidence == 0.0


def test_detector_needs_two_profiles() -> None:
    single = LanguageDetector({"es": {"a": 1}})
    assert single.detect("hola").code is None


def test_ranking_is_best_first(detector: LanguageDetector) -> None:
    result = detector.detect("buenos días, ¿cómo estás?")
    scores = [score for _, score in result.ranking]
    assert scores == sorted(scores, reverse=True)
    assert result.ranking[0][0] == "es"


# --- shared fixture: the Kotlin engine runs the same cases -------------------

FIXTURE = json.loads(
    (PACKS.parent.parent / "tests" / "parity" / "lang" / "cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", FIXTURE["detect"], ids=lambda c: c["text"][:24])
def test_fixture_detection_cases(detector: LanguageDetector, case: dict[str, object]) -> None:
    assert detector.detect(str(case["text"])).code == case["code"]


@pytest.mark.parametrize("case", FIXTURE["suggest"], ids=lambda c: c["word"])
def test_fixture_suggestion_cases(all_packs: dict[str, object], case: dict[str, object]) -> None:
    checker = SpellChecker.from_pack(all_packs[str(case["lang"])])  # type: ignore[arg-type]
    assert checker.suggest(str(case["word"]))[0] == case["first"]


def test_fixture_check_case(all_packs: dict[str, object]) -> None:
    case = FIXTURE["check"][0]
    checker = SpellChecker.from_pack(all_packs[str(case["lang"])])  # type: ignore[arg-type]
    assert [p.word for p in checker.check(str(case["text"]))] == case["words"]
