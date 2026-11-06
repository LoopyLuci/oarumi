# Parity API — Cross-Language Contract

> Hand-maintained contract. Both engines must expose these signatures. The
> Python table is checked against the live code by
> `tools/tests/test_parity_api_doc.py`; the Kotlin table is reviewed by hand
> against `engine/kotlin` until a parser exists for it.

## Python (`engine/python/oarumi/`)

| Class | Method | Signature |
|---|---|---|
| `LanguageDb` | `get_prime` | `(pid: str) -> Prime \| None` |
| `LanguageDb` | `search_lexemes` | `(query: str, limit: int = 20, root_class: str \| None = None) -> list[Lexeme]` |
| `LanguageDb` | `get_lexeme` | `(lexeme_id: int) -> Lexeme \| None` |
| `LanguageDb` | `browse_lexemes` | `(root_class: str \| None = None, limit: int = 200) -> list[Lexeme]` |
| `LanguageDb` | `root_class_counts` | `() -> dict[str, int]` |
| `LanguageDb` | `senses_for` | `(lexeme_id: int) -> list[Sense]` |
| `LanguageDb` | `get_sign` | `(lexeme_id: int) -> Sign \| None` |
| `LanguageDb` | `signs_for` | `(lexeme_id: int) -> list[Sign]` |
| `PivotTranslator` | `translate` | `(text: str, src: str, dst: str = "en") -> PivotResult` |
| `NSMDecomposerTierA` | `decompose` | `(pivot: str) -> NSMStructure` |
| `NSMRealizer` | `realize` | `(nsm: NSMStructure, modality: str) -> OarumiSurface` |
| `Pipeline` | `translate` | `(req: TranslationRequest) -> TranslationResult` |

## Kotlin (`engine/kotlin/src/main/kotlin/oarumi/`)

| Class | Method | Signature |
|---|---|---|
| `LanguageDb` | `getPrime` | `(pid: String): Prime?` |
| `LanguageDb` | `searchLexemes` | `(query: String, limit: Int = 20, rootClass: String? = null): List<Lexeme>` |
| `LanguageDb` | `getLexeme` | `(lexemeId: Int): Lexeme?` |
| `LanguageDb` | `browseLexemes` | `(rootClass: String? = null, limit: Int = 200): List<Lexeme>` |
| `LanguageDb` | `rootClassCounts` | `(): Map<String, Int>` |
| `LanguageDb` | `sensesFor` | `(lexemeId: Int): List<Sense>` |
| `LanguageDb` | `signsFor` | `(lexemeId: Int): List<Sign>` |
| `PivotTranslator` | `translate` | `(text: String, src: String, dst: String = "en"): PivotResult` |
| `NSMDecomposerTierA` | `decompose` | `(pivot: String): NsmStructure` |
| `NSMRealizer` | `realize` | `(nsm: NsmStructure, modality: String): OarumiSurface` |
| `Pipeline` | `translate` | `(req: TranslationRequest): TranslationResult` |

## Equality rule

For every case in `tests/parity/data/parity-basic/`, the JSON produced by
`Pipeline.translate` must be **byte-identical** between Python and Kotlin
after canonical serialization (sorted keys, no whitespace). See ADR-0007.
