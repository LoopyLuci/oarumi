# Dictionary entry model

> Status: design note, awaiting linguist sign-off on every form.
> Scope: what an entry is, how its parts are marked, and how the three engine
> layers read it. Content (new roots, prime spoken forms, prime decompositions,
> HamNoSys) is not part of this note.

## 1. Entry

An entry is a **lexeme** with its **senses** and **signs**. The English gloss of
a lexeme is its headword; each sense carries its own gloss.

| Part | Table | Fields | Notes |
|---|---|---|---|
| Lexeme | `lexemes` | `phon_form`, `click`, `tone`, `gloss`, `root_class`, `frequency`, `form_status` | `phon_form` is unique. `gloss` is the headword gloss. |
| Sense | `senses` | `lexeme_id`, `sense_no`, `gloss`, `prime_decomp`, `decomp_status` | Senses of one lexeme are numbered from 1 and unique per lexeme. |
| Sign | `signs` | `lexeme_id`, `hamnosys`, `nonmanual`, `form_status` | Zero or more per lexeme. No sign is created until a linguist supplies HamNoSys. |
| Prime | `primes` | `id`, `gloss`, `spoken_form`, `signed_form`, `tactile_form`, `form_status` | The NSM inventory. `form_status` covers all three surface forms. |

- **root_class** is a closed set: `noun`, `verb`, `modifier`, `particle`.
  The seed rejects any other value.
- **frequency** is the Zipf-style ordering input. Browse and search rank by it.
- **prime_decomp** holds the NSM structure fragment:
  `{"primes": [...], "combinators": [...]}`. The `primes` entries must be IDs
  from `primes`. The seed checks this.

## 2. Status vocabulary

Every form and every decomposition carries one of three statuses. The
vocabulary is the same in all tables.

| Status | Meaning | Shown in the Dictionary as |
|---|---|---|
| `placeholder` | No approved content. The row exists so the gap is explicit. | "pending linguist sign-off" |
| `provisional` | Drafted, not signed off. | "provisional" |
| `signed_off` | Approved by the linguist. | "signed off" |

Rules:

1. A placeholder is marked. The Dictionary never presents a placeholder as a
   word or a sign.
2. Defaults are conservative. Primes and senses default to `placeholder`.
   Lexemes default to `provisional`, because the 15 existing roots are the
   project's working lexicon, not signed-off content.
3. The seed never invents a form. A prime's `spoken_form` is still the
   engine's ID fallback (see § 5). It is shown as pending.

## 3. Search, browse and detail

- **Search** matches `phon_form`, the lexeme `gloss`, and any sense `gloss`.
  Exact matches (case-insensitive) rank first, then frequency, then id.
  The query is a literal substring: `%` and `_` are escaped.
- **Browse** lists lexemes of one root class, ordered by frequency, or all
  lexemes when no class is chosen.
- **Primes** is a separate browse filter. It lists the NSM inventory and
  filters it by the query.
- **Detail** shows one lexeme with its form status, root class and frequency,
  its senses in `sense_no` order with their prime decompositions, and its
  signs (or a placeholder when there are none).

## 4. Layers

The same entry methods exist in all three layers, except the Python `get_sign` convenience. `docs/PARITY_API.md` lists them.

| Layer | Source |
|---|---|
| Python | `engine/python/oarumi/db.py` (`LanguageDb`) |
| Kotlin on the JVM | `engine/kotlin/src/main/kotlin/oarumi/db/LanguageDb.kt` |
| Android (Room) | `android/app/src/main/java/com/oarumi/app/data/db/` (`Daos.kt`, `AndroidLanguageStore.kt`) |

Room validates the pre-packaged database against its entities, so every column
and index in `language/schema.sql` must have a matching entity.

## 5. Known gaps (linguist decisions)

- **Prime spoken forms.** `seed_db.py` still writes the lowercased prime ID as
  `spoken_form`. `NSMRealizer` reads that column, so changing it changes
  realized output and the frozen parity golds. Under `AGENT.md` § 4 that is a
  high-risk change. It waits for the linguist.
- **Content.** The lexicon still has 15 roots. Growing it to the planned
  600-root lexicon requires forms, which the linguist must sign off.
- **Signs.** No HamNoSys is recorded. The one existing `signs` row is the
  tactile seed's synthetic row for `manu`, with empty HamNoSys.

## 6. Schema changes

- `language/migrations/0001_init.sql` is the frozen baseline. It is no longer
  read from `schema.sql`.
- `language/migrations/0002_dictionary_entries.sql` adds the status columns,
  `sense_no`, and the indexes described above.
- `language/schema.sql` is the current full schema. A test checks that a
  database built from the migrations matches it.
