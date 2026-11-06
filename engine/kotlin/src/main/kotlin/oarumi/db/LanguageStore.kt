package oarumi.db

/**
 * Contract shared by the JVM (LanguageDb, JDBC) and Android (AndroidLanguageStore,
 * Room) implementations. Every consumer in the engine depends on this interface,
 * never on the concrete class. Entry model: docs/DICTIONARY.md.
 */
interface LanguageStore : AutoCloseable {
    fun getPrime(pid: String): Prime?

    fun allPrimes(): List<Prime>

    /** Matches phon_form, the lexeme gloss, or a sense gloss. Exact matches rank first. */
    fun searchLexemes(
        query: String,
        limit: Int = 20,
        rootClass: String? = null,
    ): List<Lexeme>

    fun getLexemeByPhon(phon: String): Lexeme?

    fun getLexeme(lexemeId: Int): Lexeme?

    /** Lexemes of one root class, or of every class when [rootClass] is null, by frequency. */
    fun browseLexemes(
        rootClass: String? = null,
        limit: Int = 200,
    ): List<Lexeme>

    /** Lexeme count per root class. */
    fun rootClassCounts(): Map<String, Int>

    /** Senses of one lexeme in sense_no order. */
    fun sensesFor(lexemeId: Int): List<Sense>

    fun signsFor(lexemeId: Int): List<Sign>

    fun getGold(
        component: String,
        inputHash: String,
    ): String?
}
