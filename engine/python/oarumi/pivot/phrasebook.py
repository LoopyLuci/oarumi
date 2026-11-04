"""Deterministic phrasebook: exact-match pivot translation for seed phrases.

The full 500-construction map is content expansion (TODO DET-003). The
structure here is the contract; the entries are seeds.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PhraseEntry:
    source: str
    target_en: str


_PHRASEBOOK: dict[str, dict[str, str]] = {
    "es": {
        "hola": "hello",
        "hola, mundo": "hello, world",
        "buenos días": "good morning",
        "buenas noches": "good night",
        "gracias": "thank you",
        "por favor": "please",
        "sí": "yes",
        "no": "no",
        "quiero agua": "I want water",
        "quiero comer": "I want to eat",
        "¿dónde está el baño?": "where is the bathroom",
        "¿cómo estás?": "how are you",
        "yo veo el libro": "I see the book",
        "él quiere ir": "he wants to go",
        "es bueno": "it is good",
        "es malo": "it is bad",
    },
    "fr": {
        "bonjour": "hello",
        "merci": "thank you",
        "s'il vous plaît": "please",
        "oui": "yes",
        "non": "no",
        "je veux de l'eau": "I want water",
        "je vois le livre": "I see the book",
        "il veut partir": "he wants to go",
        "c'est bon": "it is good",
        "c'est mauvais": "it is bad",
        "où sont les toilettes": "where is the bathroom",
        "comment ça va": "how are you",
    },
    "de": {
        "hallo": "hello",
        "danke": "thank you",
        "bitte": "please",
        "ja": "yes",
        "nein": "no",
        "ich will wasser": "I want water",
        "ich sehe das buch": "I see the book",
        "er will gehen": "he wants to go",
        "es ist gut": "it is good",
        "es ist schlecht": "it is bad",
        "wo ist die toilette": "where is the bathroom",
        "wie geht es dir": "how are you",
    },
    "zh": {
        "你好": "hello",
        "谢谢": "thank you",
        "请": "please",
        "是": "yes",
        "不": "no",
        "我要水": "I want water",
        "我看见书": "I see the book",
        "他想去": "he wants to go",
        "这是好的": "it is good",
        "这是坏的": "it is bad",
        "洗手间在哪里": "where is the bathroom",
        "你好吗": "how are you",
    },
    "ar": {
        "مرحبا": "hello",
        "شكرا": "thank you",
        "من فضلك": "please",
        "نعم": "yes",
        "لا": "no",
        "أريد الماء": "I want water",
        "أرى الكتاب": "I see the book",
        "يريد أن يذهب": "he wants to go",
        "إنه جيد": "it is good",
        "إنه سيء": "it is bad",
        "أين الحمام": "where is the bathroom",
        "كيف حالك": "how are you",
    },
}


def lookup(lang: str, text: str) -> str | None:
    """Return the English pivot for `text` in `lang`, or None if not in the book."""
    table = _PHRASEBOOK.get(lang)
    if table is None:
        return None
    return table.get(text.strip().lower())


def supported_languages() -> tuple[str, ...]:
    return tuple(sorted(_PHRASEBOOK.keys()))
