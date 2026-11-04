package oarumi.db

/**
 * Contract shared by the JVM (LanguageDb, JDBC) and Android (AndroidLanguageStore,
 * Room) implementations. Every consumer in the engine depends on this interface,
 * never on the concrete class.
 */
interface LanguageStore : AutoCloseable {
    fun getPrime(pid: String): Prime?

    fun allPrimes(): List<Prime>

    fun searchLexemes(
        query: String,
        limit: Int = 20,
    ): List<Lexeme>

    fun getLexemeByPhon(phon: String): Lexeme?

    fun getGold(
        component: String,
        inputHash: String,
    ): String?
}
