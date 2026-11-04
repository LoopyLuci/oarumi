package oarumi.db

import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import oarumi.types.OarumiJson
import java.nio.file.Path
import java.sql.Connection
import java.sql.DriverManager
import java.sql.ResultSet

data class Prime(
    val id: String,
    val gloss: String,
    val category: String,
    val combinators: List<String>,
    val spokenForm: String,
    val signedForm: String,
    val tactileForm: String,
    val nsmVersion: String,
)

data class Lexeme(
    val id: Int,
    val phonForm: String,
    val click: String?,
    val tone: String?,
    val gloss: String,
    val rootClass: String,
    val frequency: Int,
)

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
                      tactile_form, nsm_version
               FROM primes WHERE id = ?""",
        ).use { ps ->
            ps.setString(1, pid)
            ps.executeQuery().use { rs -> if (rs.next()) rsToPrime(rs) else null }
        }

    override fun allPrimes(): List<Prime> =
        conn.prepareStatement(
            """SELECT id, gloss, category, combinators, spoken_form, signed_form,
                      tactile_form, nsm_version FROM primes ORDER BY id""",
        ).use { ps -> ps.executeQuery().use { rs -> buildList { while (rs.next()) add(rsToPrime(rs)) } } }

    override fun searchLexemes(
        query: String,
        limit: Int,
    ): List<Lexeme> {
        val like = "%$query%"
        return conn.prepareStatement(
            """SELECT id, phon_form, click, tone, gloss, root_class, frequency
               FROM lexemes
               WHERE phon_form LIKE ? OR gloss LIKE ?
               ORDER BY frequency DESC, id ASC
               LIMIT ?""",
        ).use { ps ->
            ps.setString(1, like)
            ps.setString(2, like)
            ps.setInt(3, limit)
            ps.executeQuery().use { rs ->
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
                            ),
                        )
                    }
                }
            }
        }
    }

    override fun getLexemeByPhon(phon: String): Lexeme? =
        conn.prepareStatement(
            """SELECT id, phon_form, click, tone, gloss, root_class, frequency
               FROM lexemes WHERE phon_form = ?""",
        ).use { ps ->
            ps.setString(1, phon)
            ps.executeQuery().use { rs ->
                if (rs.next()) {
                    Lexeme(
                        id = rs.getInt("id"),
                        phonForm = rs.getString("phon_form"),
                        click = rs.getString("click"),
                        tone = rs.getString("tone"),
                        gloss = rs.getString("gloss"),
                        rootClass = rs.getString("root_class"),
                        frequency = rs.getInt("frequency"),
                    )
                } else {
                    null
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
        )
    }
}
