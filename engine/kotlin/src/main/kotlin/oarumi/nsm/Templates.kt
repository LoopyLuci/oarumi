package oarumi.nsm

import oarumi.types.Combinator
import oarumi.types.NsmStructure
import oarumi.types.PrimeRef

data class Template(
    val name: String,
    val pattern: Regex,
    val build: (MatchResult) -> NsmStructure,
)

private val FIRST_PERSON = setOf("i", "yo", "je", "ich")

private fun ref(
    id: String,
    role: String,
) = PrimeRef(id, role)

private fun clause(
    head: String,
    vararg args: String,
) = Combinator("clause", head, args.toList())

private fun buildWant(m: MatchResult): NsmStructure {
    val who = (m.groups["who"]?.value ?: "someone").trim()
    val agent = if (who.lowercase() in FIRST_PERSON) "I" else "SOMEONE"
    val obj = "SOMETHING"
    return NsmStructure(
        primes = listOf(ref(agent, "agent"), ref("WANT", "predicate"), ref(obj, "patient")),
        combinators = listOf(clause("WANT", agent, obj)),
    )
}

private fun buildSee(m: MatchResult): NsmStructure {
    val who = (m.groups["who"]?.value ?: "someone").trim()
    val agent = if (who.lowercase() in FIRST_PERSON) "I" else "SOMEONE"
    return NsmStructure(
        primes = listOf(ref(agent, "agent"), ref("SEE", "predicate"), ref("SOMETHING", "patient")),
        combinators = listOf(clause("SEE", agent, "SOMETHING")),
    )
}

private fun buildGo(m: MatchResult): NsmStructure {
    val who = (m.groups["who"]?.value ?: "someone").trim()
    val agent = if (who.lowercase() in FIRST_PERSON) "I" else "SOMEONE"
    return NsmStructure(
        primes = listOf(ref(agent, "agent"), ref("MOVE", "predicate"), ref("WHERE", "modifier")),
        combinators = listOf(clause("MOVE", agent, "WHERE")),
    )
}

private fun buildIsGood(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("SOMETHING", "patient"), ref("BE_SPEC", "predicate"), ref("GOOD", "argument")),
    combinators = listOf(Combinator("predicate", "BE_SPEC", listOf("SOMETHING", "GOOD"))),
)

private fun buildIsBad(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("SOMETHING", "patient"), ref("BE_SPEC", "predicate"), ref("BAD", "argument")),
    combinators = listOf(Combinator("predicate", "BE_SPEC", listOf("SOMETHING", "BAD"))),
)

private fun buildGreeting(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("I", "agent"), ref("SAY", "predicate"), ref("WORDS", "patient")),
    combinators = listOf(clause("SAY", "I", "WORDS")),
)

private fun buildThanks(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("I", "agent"), ref("FEEL", "predicate"), ref("GOOD", "argument")),
    combinators = listOf(Combinator("predicate", "FEEL", listOf("I", "GOOD"))),
)

private fun buildYes(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("TRUE", "predicate")),
    combinators = listOf(Combinator("predicate", "TRUE", emptyList())),
)

private fun buildNo(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("NOT", "operator"), ref("TRUE", "predicate")),
    combinators = listOf(Combinator("predicate", "NOT", listOf("TRUE"))),
)

private fun buildQuestionHow(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes = listOf(ref("YOU", "agent"), ref("FEEL", "predicate")),
    combinators = listOf(Combinator("predicate", "FEEL", listOf("YOU"))),
)

private fun buildQuestionWhere(
    @Suppress("UNUSED_PARAMETER") m: MatchResult,
) = NsmStructure(
    primes =
        listOf(
            ref("SOMETHING", "patient"),
            ref("BE_SOMEWHERE", "predicate"),
            ref("WHERE", "modifier"),
        ),
    combinators = listOf(Combinator("predicate", "BE_SOMEWHERE", listOf("SOMETHING", "WHERE"))),
)

val TEMPLATES: List<Template> =
    listOf(
        Template(
            "want",
            Regex(
                """^(?<who>i|he|she|they|you|someone)\s+(?:want|wants|would like)\s+(?:to\s+)?(?<what>.+?)""" +
                    """(?:\s+(?:go|eat|sleep|leave|come))?$""",
                RegexOption.IGNORE_CASE,
            ),
            ::buildWant,
        ),
        Template(
            "want_simple",
            Regex(
                """^(?<who>i|he|she|they|you)\s+(?:want|wants)\s+(?<what>[^.?!]+)$""",
                RegexOption.IGNORE_CASE,
            ),
            ::buildWant,
        ),
        Template(
            "see",
            Regex(
                """^(?<who>i|he|she|they|you)\s+(?:see|sees)\s+(?:the\s+)?(?<what>[^.?!]+)$""",
                RegexOption.IGNORE_CASE,
            ),
            ::buildSee,
        ),
        Template(
            "go",
            Regex("""^(?<who>i|he|she|they|you)\s+(?:want to\s+)?go$""", RegexOption.IGNORE_CASE),
            ::buildGo,
        ),
        Template("is_good", Regex("""^(?:it\s+is|it's|this\s+is)\s+good$""", RegexOption.IGNORE_CASE), ::buildIsGood),
        Template("is_bad", Regex("""^(?:it\s+is|it's|this\s+is)\s+bad$""", RegexOption.IGNORE_CASE), ::buildIsBad),
        Template(
            "hello",
            Regex("""^(?:hello|hi|good morning|good night)$""", RegexOption.IGNORE_CASE),
            ::buildGreeting,
        ),
        Template("thanks", Regex("""^(?:thank you|thanks)$""", RegexOption.IGNORE_CASE), ::buildThanks),
        Template("yes", Regex("""^yes$""", RegexOption.IGNORE_CASE), ::buildYes),
        Template("no", Regex("""^no$""", RegexOption.IGNORE_CASE), ::buildNo),
        Template("how_are_you", Regex("""^how\s+are\s+you$""", RegexOption.IGNORE_CASE), ::buildQuestionHow),
        Template(
            "where_is",
            Regex("""^where\s+is\s+(?:the\s+)?[^.?!]+$""", RegexOption.IGNORE_CASE),
            ::buildQuestionWhere,
        ),
    )
