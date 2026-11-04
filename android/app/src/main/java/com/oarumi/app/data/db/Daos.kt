package com.oarumi.app.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface PrimeDao {
    @Query("SELECT * FROM primes WHERE id = :id")
    fun getById(id: String): PrimeEntity?

    @Query("SELECT * FROM primes ORDER BY id ASC")
    fun all(): List<PrimeEntity>
}

@Dao
interface LexemeDao {
    @Query(
        """
        SELECT * FROM lexemes
        WHERE phon_form LIKE '%' || :query || '%' OR gloss LIKE '%' || :query || '%'
        ORDER BY frequency DESC, id ASC
        LIMIT :limit
        """,
    )
    fun search(
        query: String,
        limit: Int,
    ): List<LexemeEntity>

    @Query("SELECT * FROM lexemes WHERE phon_form = :phon LIMIT 1")
    fun byPhon(phon: String): LexemeEntity?
}

@Dao
interface SignDao {
    @Query("SELECT * FROM signs WHERE lexeme_id = :lexemeId LIMIT 1")
    fun byLexeme(lexemeId: Int): SignEntity?
}

@Dao
interface TactileDao {
    @Query("SELECT * FROM tactile WHERE sign_id = :signId")
    fun bySign(signId: Int): List<TactileEntity>
}

@Dao
interface GoldDao {
    @Query(
        "SELECT output_json FROM parity_gold WHERE component = :component AND input_hash = :hash LIMIT 1",
    )
    fun output(
        component: String,
        hash: String,
    ): String?
}
