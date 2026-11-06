package com.oarumi.app.data.db

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Query

@Dao
interface PrimeDao {
    @Query("SELECT * FROM primes WHERE id = :id")
    fun getById(id: String): PrimeEntity?

    @Query("SELECT * FROM primes ORDER BY id ASC")
    fun all(): List<PrimeEntity>
}

/** Lexeme count for one root class. */
data class RootClassCountRow(
    @ColumnInfo(name = "root_class") val rootClass: String,
    @ColumnInfo(name = "n") val count: Int,
)

@Dao
interface LexemeDao {
    /**
     * [like] is a LIKE pattern with its wildcards already escaped (see likePattern in
     * the engine). [exact] is the raw query, used to rank exact matches first.
     */
    @Query(
        """
        SELECT * FROM lexemes
        WHERE (phon_form LIKE :like ESCAPE '\' OR gloss LIKE :like ESCAPE '\'
               OR id IN (SELECT lexeme_id FROM senses WHERE gloss LIKE :like ESCAPE '\'))
          AND (:rootClass IS NULL OR root_class = :rootClass)
        ORDER BY CASE WHEN LOWER(phon_form) = LOWER(:exact) OR LOWER(gloss) = LOWER(:exact)
                      THEN 0 ELSE 1 END,
                 frequency DESC, id ASC
        LIMIT :limit
        """,
    )
    fun search(
        like: String,
        exact: String,
        rootClass: String?,
        limit: Int,
    ): List<LexemeEntity>

    @Query("SELECT * FROM lexemes WHERE phon_form = :phon LIMIT 1")
    fun byPhon(phon: String): LexemeEntity?

    @Query("SELECT * FROM lexemes WHERE id = :id LIMIT 1")
    fun byId(id: Int): LexemeEntity?

    @Query(
        """
        SELECT * FROM lexemes
        WHERE (:rootClass IS NULL OR root_class = :rootClass)
        ORDER BY frequency DESC, id ASC
        LIMIT :limit
        """,
    )
    fun browse(
        rootClass: String?,
        limit: Int,
    ): List<LexemeEntity>

    @Query("SELECT root_class, COUNT(*) AS n FROM lexemes GROUP BY root_class ORDER BY root_class")
    fun rootClassCounts(): List<RootClassCountRow>
}

@Dao
interface SenseDao {
    @Query("SELECT * FROM senses WHERE lexeme_id = :lexemeId ORDER BY sense_no, id")
    fun forLexeme(lexemeId: Int): List<SenseEntity>
}

@Dao
interface SignDao {
    @Query("SELECT * FROM signs WHERE lexeme_id = :lexemeId ORDER BY id")
    fun forLexeme(lexemeId: Int): List<SignEntity>
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
