"""Generate the parity-basic corpus deterministically.

Idempotent: running twice produces the same files. Every case has a
`request` object; `expected` is filled in by tools/freeze_gold.py.

    python tools/generate_parity_corpus.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "parity" / "data" / "parity-basic"

# Phrasebook-sourced inputs. Each language has 12 seed phrases (see
# engine/python/oarumi/pivot/phrasebook.py) plus 2 extra probes, giving 14.
# We cross these with modalities: 5 languages x 14 phrases x 3 = 210 cases,
# plus 4 degraded-path cases = 214 (the Batch 13 target is >= 200).
PHRASES = {
    "es": [
        "hola",
        "quiero agua",
        "yo veo el libro",
        "es bueno",
        "es malo",
        "gracias",
        "por favor",
        "sí",
        "no",
        "¿cómo estás?",
        "¿dónde está el baño?",
        "buenos días",
        "¿qué hora es?",
        "me llamo ana",
    ],
    "fr": [
        "bonjour",
        "merci",
        "oui",
        "non",
        "je veux de l'eau",
        "je vois le livre",
        "il veut partir",
        "c'est bon",
        "c'est mauvais",
        "comment ça va",
        "où sont les toilettes",
        "s'il vous plaît",
        "quelle heure est-il ?",
        "je m'appelle ana",
    ],
    "de": [
        "hallo",
        "danke",
        "bitte",
        "ja",
        "nein",
        "ich will wasser",
        "ich sehe das buch",
        "er will gehen",
        "es ist gut",
        "es ist schlecht",
        "wie geht es dir",
        "wo ist die toilette",
        "wie spät ist es",
        "ich heiße ana",
    ],
    "zh": [
        "你好",
        "谢谢",
        "请",
        "是",
        "不",
        "我要水",
        "我看见书",
        "他想去",
        "这是好的",
        "这是坏的",
        "你好吗",
        "洗手间在哪里",
        "现在几点",
        "我叫安娜",
    ],
    "ar": [
        "مرحبا",
        "شكرا",
        "من فضلك",
        "نعم",
        "لا",
        "أريد الماء",
        "أرى الكتاب",
        "يريد أن يذهب",
        "إنه جيد",
        "إنه سيء",
        "كيف حالك",
        "أين الحمام",
        "كم الساعة",
        "اسمي آنا",
    ],
}

MODALITIES = ["spoken", "signed", "tactile"]


def _case_id(lang: str, idx: int, modality: str) -> str:
    return f"{lang}_{idx:02d}_{modality}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for lang, phrases in PHRASES.items():
        for idx, phrase in enumerate(phrases, start=1):
            for modality in MODALITIES:
                case = {
                    "request": {
                        "text": phrase,
                        "lang": lang,
                        "modality": modality,
                    },
                }
                path = OUT / f"{_case_id(lang, idx, modality)}.json"
                path.write_text(
                    json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                count += 1

    # Extra: degraded-path cases (unknown language, unsupported target).
    extra = [
        {
            "id": "extra_unsupported_lang",
            "request": {"text": "hola", "lang": "xx", "modality": "spoken"},
        },
        {"id": "extra_empty_input", "request": {"text": "", "lang": "es", "modality": "spoken"}},
        {
            "id": "extra_whitespace_input",
            "request": {"text": "   ", "lang": "es", "modality": "spoken"},
        },
        {
            "id": "extra_same_lang_passthrough",
            "request": {"text": "hello", "lang": "en", "modality": "spoken"},
        },
    ]
    for e in extra:
        path = OUT / f"{e['id']}.json"
        path.write_text(
            json.dumps({"request": e["request"]}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        count += 1

    print(f"OK   wrote {count} cases to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
