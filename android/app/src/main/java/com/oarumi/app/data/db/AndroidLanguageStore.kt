package com.oarumi.app.data.db

import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import oarumi.db.LanguageStore
import oarumi.db.Lexeme
import oarumi.db.Prime
import oarumi.types.OarumiJson

/**
 * Room-backed implementation of the engine's LanguageStore.
 * Field names and behavior match LanguageDb (JVM); parity is enforced by tests.
 */
class AndroidLanguageStore(private val db: AppDatabase) : LanguageStore {
    override fun getPrime(pid: String): Prime? = db.primeDao().getById(pid)?.let(::toPrime)

    override fun allPrimes(): List<Prime> = db.primeDao().all().map(::toPrime)

    override fun searchLexemes(
        query: String,
        limit: Int,
    ): List<Lexeme> = db.lexemeDao().search(query, limit).map(::toLexeme)

    override fun getLexemeByPhon(phon: String): Lexeme? = db.lexemeDao().byPhon(phon)?.let(::toLexeme)

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
        )
}
