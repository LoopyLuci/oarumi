package com.oarumi.app.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entities mirror language/schema.sql column-for-column.
 * Do not rename columns; the JVM LanguageDb reads the same rows.
 */
@Entity(tableName = "primes")
data class PrimeEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: String,
    @ColumnInfo(name = "gloss") val gloss: String,
    @ColumnInfo(name = "category") val category: String,
    // JSON array string
    @ColumnInfo(name = "combinators") val combinators: String,
    @ColumnInfo(name = "spoken_form") val spokenForm: String,
    @ColumnInfo(name = "signed_form") val signedForm: String,
    @ColumnInfo(name = "tactile_form") val tactileForm: String,
    @ColumnInfo(name = "nsm_version") val nsmVersion: String,
)

@Entity(tableName = "lexemes")
data class LexemeEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: Int,
    @ColumnInfo(name = "phon_form") val phonForm: String,
    @ColumnInfo(name = "click") val click: String?,
    @ColumnInfo(name = "tone") val tone: String?,
    @ColumnInfo(name = "gloss") val gloss: String,
    @ColumnInfo(name = "root_class") val rootClass: String,
    @ColumnInfo(name = "frequency") val frequency: Int,
)

@Entity(
    tableName = "senses",
    foreignKeys = [
        ForeignKey(
            entity = LexemeEntity::class,
            parentColumns = ["id"],
            childColumns = ["lexeme_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["lexeme_id"], name = "idx_senses_lexeme")],
)
data class SenseEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: Int,
    @ColumnInfo(name = "lexeme_id") val lexemeId: Int,
    @ColumnInfo(name = "prime_decomp") val primeDecomp: String,
    @ColumnInfo(name = "gloss") val gloss: String,
)

@Entity(
    tableName = "signs",
    foreignKeys = [
        ForeignKey(
            entity = LexemeEntity::class,
            parentColumns = ["id"],
            childColumns = ["lexeme_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["lexeme_id"], name = "idx_signs_lexeme")],
)
data class SignEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: Int,
    @ColumnInfo(name = "lexeme_id") val lexemeId: Int,
    @ColumnInfo(name = "hamnosys") val hamnosys: String,
    @ColumnInfo(name = "nonmanual") val nonmanual: String,
)

@Entity(
    tableName = "tactile",
    foreignKeys = [
        ForeignKey(
            entity = SignEntity::class,
            parentColumns = ["id"],
            childColumns = ["sign_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["sign_id"], name = "idx_tactile_sign")],
)
data class TactileEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: Int,
    @ColumnInfo(name = "sign_id") val signId: Int,
    @ColumnInfo(name = "protocol_json") val protocolJson: String,
)

@Entity(
    tableName = "parity_gold",
    indices = [Index(value = ["component"], name = "idx_gold_component")],
)
data class GoldEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: Int,
    @ColumnInfo(name = "component") val component: String,
    @ColumnInfo(name = "input_hash") val inputHash: String,
    @ColumnInfo(name = "output_json") val outputJson: String,
    @ColumnInfo(name = "frozen_at") val frozenAt: String,
)

@Entity(tableName = "schema_migrations")
data class MigrationEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: String,
    @ColumnInfo(name = "applied_at") val appliedAt: String,
    @ColumnInfo(name = "checksum") val checksum: String,
)
