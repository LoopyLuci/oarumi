package com.oarumi.app.data.db

import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import oarumi.db.LanguageStore
import oarumi.db.Lexeme
import oarumi.db.Prime
import oarumi.db.Sense
import oarumi.db.Sign
import oarumi.db.likePattern
import oarumi.types.OarumiJson

/**
 * Room-backed implementation of the engine's LanguageStore.
 * Field names and behavior match LanguageDb (JVM); parity is enforced by tests.
 * Entry model: docs/DICTIONARY.md.
 */
class AndroidLanguageStore(private val db: AppDatabase) : LanguageStore {
    override fun getPrime(pid: String): Prime? = db.primeDao().getById(pid)?.let(::toPrime)

    override fun allPrimes(): List<Prime> = db.primeDao().all().map(::toPrime)

    override fun searchLexemes(
        query: String,
        limit: Int,
        rootClass: String?,
    ): List<Lexeme> {
        val needle = query.trim()
        return db.lexemeDao().search(likePattern(needle), needle, rootClass, limit).map(::toLexeme)
    }

    override fun getLexemeByPhon(phon: String): Lexeme? = db.lexemeDao().byPhon(phon)?.let(::toLexeme)

    override fun getLexeme(lexemeId: Int): Lexeme? = db.lexemeDao().byId(lexemeId)?.let(::toLexeme)

    override fun browseLexemes(
        rootClass: String?,
        limit: Int,
    ): List<Lexeme> = db.lexemeDao().browse(rootClass, limit).map(::toLexeme)

    override fun rootClassCounts(): Map<String, Int> =
        db.lexemeDao().rootClassCounts().associate { it.rootClass to it.count }

    override fun sensesFor(lexemeId: Int): List<Sense> = db.senseDao().forLexeme(lexemeId).map(::toSense)

    override fun signsFor(lexemeId: Int): List<Sign> = db.signDao().forLexeme(lexemeId).map(::toSign)

    override fun getGold(
        component: String,
        inputHash: String,
    ): String? = db.goldDao().output(component, inputHash)

    override fun close() {
        // Room owns the connection; closing happens when the DB is destroyed.
    }

    private fun toPrime(e: PrimeEntity): Prime {
        val combinators =
            OarumiJson
                .parseToJsonElement(e.combinators)
                .jsonArray
                .map { it.jsonPrimitive.content }
        return Prime(
            id = e.id,
            gloss = e.gloss,
            category = e.category,
            combinators = combinators,
            spokenForm = e.spokenForm,
            signedForm = e.signedForm,
            tactileForm = e.tactileForm,
            nsmVersion = e.nsmVersion,
            formStatus = e.formStatus,
        )
    }

    private fun toLexeme(e: LexemeEntity): Lexeme =
        Lexeme(
            id = e.id,
            phonForm = e.phonForm,
            click = e.click,
            tone = e.tone,
            gloss = e.gloss,
            rootClass = e.rootClass,
            frequency = e.frequency,
            formStatus = e.formStatus,
        )

    private fun toSense(e: SenseEntity): Sense {
        // A decomposition without a "primes" array reads as empty, not as an error.
        val primes =
            OarumiJson
                .parseToJsonElement(e.primeDecomp)
                .jsonObject["primes"]
                ?.jsonArray
                ?.map { it.jsonPrimitive.content }
                ?: emptyList()
        return Sense(
            id = e.id,
            lexemeId = e.lexemeId,
            senseNo = e.senseNo,
            gloss = e.gloss,
            primes = primes,
            decompStatus = e.decompStatus,
        )
    }

    private fun toSign(e: SignEntity): Sign =
        Sign(
            id = e.id,
            lexemeId = e.lexemeId,
            hamnosys = e.hamnosys,
            nonmanual = e.nonmanual,
            formStatus = e.formStatus,
        )
}
