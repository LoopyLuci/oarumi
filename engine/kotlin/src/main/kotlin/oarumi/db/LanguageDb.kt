package oarumi.db

import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import oarumi.types.OarumiJson
import java.nio.file.Path
import java.sql.Connection
import java.sql.DriverManager
import java.sql.ResultSet

/** Entry model and status vocabulary: docs/DICTIONARY.md. */
data class Prime(
    val id: String,
    val gloss: String,
    val category: String,
    val combinators: List<String>,
    val spokenForm: String,
    val signedForm: String,
    val tactileForm: String,
    val nsmVersion: String,
    val formStatus: String = "placeholder",
)

data class Lexeme(
    val id: Int,
    val phonForm: String,
    val click: String?,
    val tone: String?,
    val gloss: String,
    val rootClass: String,
    val frequency: Int,
    val formStatus: String = "provisional",
)

/** One meaning of a lexeme. [primes] is the decomposition, in order. */
data class Sense(
    val id: Int,
    val lexemeId: Int,
    val senseNo: Int,
    val gloss: String,
    val primes: List<String>,
    val decompStatus: String,
)

data class Sign(
    val id: Int,
    val lexemeId: Int,
    val hamnosys: String,
    val nonmanual: String,
    val formStatus: String = "placeholder",
)

private const val LEXEME_COLUMNS =
    "id, phon_form, click, tone, gloss, root_class, frequency, form_status"

/** Escapes LIKE wildcards so the query is matched as a literal substring. */
fun likePattern(text: String): String = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

class LanguageDb(path: Path) : LanguageStore {
    init {
        require(path.toFile().exists()) { "language DB not found: $path" }
    }

    private val conn: Connection =
        DriverManager.getConnection("jdbc:sqlite:${path.toAbsolutePath()}")

    init {
        conn.createStatement().use { it.execute("PRAGMA foreign_keys = ON") }
    }

    override fun close() = conn.close()

    override fun getPrime(pid: String): Prime? =
        conn.prepareStatement(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version, form_status
               FROM primes WHERE id = ?""",
        ).use { ps ->
            ps.setString(1, pid)
            ps.executeQuery().use { rs -> if (rs.next()) rsToPrime(rs) else null }
        }

    override fun allPrimes(): List<Prime> =
        conn.prepareStatement(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version, form_status FROM primes ORDER BY id""",
        ).use { ps -> ps.executeQuery().use { rs -> buildList { while (rs.next()) add(rsToPrime(rs)) } } }

    override fun searchLexemes(
        query: String,
        limit: Int,
        rootClass: String?,
    ): List<Lexeme> {
        val needle = query.trim()
        val like = likePattern(needle)
        return conn.prepareStatement(
            """SELECT $LEXEME_COLUMNS FROM lexemes
               WHERE (phon_form LIKE ? ESCAPE '\' OR gloss LIKE ? ESCAPE '\'
                      OR id IN (SELECT lexeme_id FROM senses WHERE gloss LIKE ? ESCAPE '\'))
                 AND (? IS NULL OR root_class = ?)
               ORDER BY CASE WHEN LOWER(phon_form) = LOWER(?) OR LOWER(gloss) = LOWER(?)
                             THEN 0 ELSE 1 END,
                        frequency DESC, id ASC
               LIMIT ?""",
        ).use { ps ->
            ps.setString(1, like)
            ps.setString(2, like)
            ps.setString(3, like)
            ps.setString(4, rootClass)
            ps.setString(5, rootClass)
            ps.setString(6, needle)
            ps.setString(7, needle)
            ps.setInt(8, limit)
            ps.executeQuery().use { rs -> readLexemes(rs) }
        }
    }

    override fun getLexemeByPhon(phon: String): Lexeme? =
        conn.prepareStatement("SELECT $LEXEME_COLUMNS FROM lexemes WHERE phon_form = ?").use { ps ->
            ps.setString(1, phon)
            ps.executeQuery().use { rs -> readLexemes(rs).firstOrNull() }
        }

    override fun getLexeme(lexemeId: Int): Lexeme? =
        conn.prepareStatement("SELECT $LEXEME_COLUMNS FROM lexemes WHERE id = ?").use { ps ->
            ps.setInt(1, lexemeId)
            ps.executeQuery().use { rs -> readLexemes(rs).firstOrNull() }
        }

    override fun browseLexemes(
        rootClass: String?,
        limit: Int,
    ): List<Lexeme> =
        conn.prepareStatement(
            """SELECT $LEXEME_COLUMNS FROM lexemes
               WHERE (? IS NULL OR root_class = ?)
               ORDER BY frequency DESC, id ASC
               LIMIT ?""",
        ).use { ps ->
            ps.setString(1, rootClass)
            ps.setString(2, rootClass)
            ps.setInt(3, limit)
            ps.executeQuery().use { rs -> readLexemes(rs) }
        }

    override fun rootClassCounts(): Map<String, Int> =
        conn.prepareStatement(
            "SELECT root_class, COUNT(*) AS n FROM lexemes GROUP BY root_class ORDER BY root_class",
        ).use { ps ->
            ps.executeQuery().use { rs ->
                buildMap {
                    while (rs.next()) put(rs.getString("root_class"), rs.getInt("n"))
                }
            }
        }

    override fun sensesFor(lexemeId: Int): List<Sense> =
        conn.prepareStatement(
            """SELECT id, lexeme_id, sense_no, gloss, prime_decomp, decomp_status
               FROM senses WHERE lexeme_id = ? ORDER BY sense_no, id""",
        ).use { ps ->
            ps.setInt(1, lexemeId)
            ps.executeQuery().use { rs ->
                buildList {
                    while (rs.next()) {
                        // A decomposition without a "primes" array reads as empty, not as an error.
                        val primes =
                            OarumiJson.parseToJsonElement(rs.getString("prime_decomp"))
                                .jsonObject["primes"]?.jsonArray
                                ?.map { it.jsonPrimitive.content }
                                ?: emptyList()
                        add(
                            Sense(
                                id = rs.getInt("id"),
                                lexemeId = rs.getInt("lexeme_id"),
                                senseNo = rs.getInt("sense_no"),
                                gloss = rs.getString("gloss"),
                                primes = primes,
                                decompStatus = rs.getString("decomp_status"),
                            ),
                        )
                    }
                }
            }
        }

    override fun signsFor(lexemeId: Int): List<Sign> =
        conn.prepareStatement(
            "SELECT id, lexeme_id, hamnosys, nonmanual, form_status FROM signs WHERE lexeme_id = ? ORDER BY id",
        ).use { ps ->
            ps.setInt(1, lexemeId)
            ps.executeQuery().use { rs ->
                buildList {
                    while (rs.next()) {
                        add(
                            Sign(
                                id = rs.getInt("id"),
                                lexemeId = rs.getInt("lexeme_id"),
                                hamnosys = rs.getString("hamnosys"),
                                nonmanual = rs.getString("nonmanual"),
                                formStatus = rs.getString("form_status"),
                            ),
                        )
                    }
                }
            }
        }

    override fun getGold(
        component: String,
        inputHash: String,
    ): String? =
        conn.prepareStatement(
            "SELECT output_json FROM parity_gold WHERE component = ? AND input_hash = ?",
        ).use { ps ->
            ps.setString(1, component)
            ps.setString(2, inputHash)
            ps.executeQuery().use { rs -> if (rs.next()) rs.getString(1) else null }
        }

    private fun readLexemes(rs: ResultSet): List<Lexeme> =
        buildList {
            while (rs.next()) {
                add(
                    Lexeme(
                        id = rs.getInt("id"),
                        phonForm = rs.getString("phon_form"),
                        click = rs.getString("click"),
                        tone = rs.getString("tone"),
                        gloss = rs.getString("gloss"),
                        rootClass = rs.getString("root_class"),
                        frequency = rs.getInt("frequency"),
                        formStatus = rs.getString("form_status"),
                    ),
                )
            }
        }

    private fun rsToPrime(rs: ResultSet): Prime {
        val combinatorsJson = rs.getString("combinators")
        val combinators =
            OarumiJson.parseToJsonElement(combinatorsJson).jsonArray
                .map { it.jsonPrimitive.content }
        return Prime(
            id = rs.getString("id"),
            gloss = rs.getString("gloss"),
            category = rs.getString("category"),
            combinators = combinators,
            spokenForm = rs.getString("spoken_form"),
            signedForm = rs.getString("signed_form"),
            tactileForm = rs.getString("tactile_form"),
            nsmVersion = rs.getString("nsm_version"),
            formStatus = rs.getString("form_status"),
        )
    }
}
