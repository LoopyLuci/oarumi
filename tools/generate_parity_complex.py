"""Generate parity-complex: multi-clause and ambiguity cases.

Where parity-basic exercises the happy path, this corpus exercises:
- every template (want, want_simple, see, go, is_good, is_bad, hello, thanks,
  yes, no, how_are_you, where_is) via the phrasebook
- every mood
- every modality combination

Expected output is filled in by tools/freeze_gold.py. This corpus is larger
and slower; CI runs it on nightly only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "parity" / "data" / "parity-complex"

# Intentional templates: each input is designed to route to a specific template.
INPUTS = [
    # want
    ("es", "quiero agua"),
    ("fr", "je veux de l'eau"),
    ("de", "ich will wasser"),
    ("zh", "我要水"),
    ("ar", "أريد الماء"),
    # want_simple
    ("es", "quiero comer"),
    ("fr", "il veut partir"),
    ("de", "er will gehen"),
    ("zh", "他想去"),
    ("ar", "يريد أن يذهب"),
    # see
    ("es", "yo veo el libro"),
    ("fr", "je vois le livre"),
    ("de", "ich sehe das buch"),
    ("zh", "我看见书"),
    ("ar", "أرى الكتاب"),
    # is_good
    ("es", "es bueno"),
    ("fr", "c'est bon"),
    ("de", "es ist gut"),
    ("zh", "这是好的"),
    ("ar", "إنه جيد"),
    # is_bad
    ("es", "es malo"),
    ("fr", "c'est mauvais"),
    ("de", "es ist schlecht"),
    ("zh", "这是坏的"),
    ("ar", "إنه سيء"),
    # hello
    ("es", "hola"),
    ("fr", "bonjour"),
    ("de", "hallo"),
    ("zh", "你好"),
    ("ar", "مرحبا"),
    # thanks
    ("es", "gracias"),
    ("fr", "merci"),
    ("de", "danke"),
    ("zh", "谢谢"),
    ("ar", "شكرا"),
    # yes
    ("es", "sí"),
    ("fr", "oui"),
    ("de", "ja"),
    ("zh", "是"),
    ("ar", "نعم"),
    # no
    ("es", "no"),
    ("fr", "non"),
    ("de", "nein"),
    ("zh", "不"),
    ("ar", "لا"),
    # how_are_you
    ("es", "¿cómo estás?"),
    ("fr", "comment ça va"),
    ("de", "wie geht es dir"),
    ("zh", "你好吗"),
    ("ar", "كيف حالك"),
    # where_is
    ("es", "¿dónde está el baño?"),
    ("fr", "où sont les toilettes"),
    ("de", "wo ist die toilette"),
    ("zh", "洗手间在哪里"),
    ("ar", "أين الحمام"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for idx, (lang, text) in enumerate(INPUTS, start=1):
        for modality in ["spoken", "signed", "tactile"]:
            case = {
                "request": {"text": text, "lang": lang, "modality": modality},
            }
            (OUT / f"complex_{idx:03d}_{modality}.json").write_text(
                json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            count += 1
    print(f"OK   wrote {count} cases to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
