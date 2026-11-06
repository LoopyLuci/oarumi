package oarumi.db

import java.nio.file.Path
import kotlin.test.AfterTest
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Search, browse and detail against language/oarumi.db. Entry model: docs/DICTIONARY.md. */
class LanguageDbTest {
    private lateinit var db: LanguageDb

    @BeforeTest
    fun open() {
        db = LanguageDb(Path.of(System.getProperty("oarumi.db")))
    }

    @AfterTest
    fun close() {
        db.close()
    }

    @Test
    fun `exact match ranks first`() {
        assertEquals("manu", db.searchLexemes("who").first().phonForm)
    }

    @Test
    fun `search matches a sense gloss`() {
        val hits = db.searchLexemes("interrogative person").map { it.phonForm }
        assertTrue("manu" in hits, "expected manu in $hits")
    }

    @Test
    fun `wildcards match literally`() {
        assertTrue(db.searchLexemes("%").isEmpty())
        assertTrue(db.searchLexemes("_").isEmpty())
    }

    @Test
    fun `like pattern escapes the wildcards and the escape character`() {
        assertEquals("%a\\_b\\%c\\\\%", likePattern("a_b%c\\"))
    }

    @Test
    fun `search filters by root class`() {
        val hits = db.searchLexemes("", limit = 100, rootClass = "particle")
        assertTrue(hits.isNotEmpty())
        assertTrue(hits.all { it.rootClass == "particle" })
    }

    @Test
    fun `browse is ordered by frequency and counts add up`() {
        val all = db.browseLexemes(limit = 1000)
        val freqs = all.map { it.frequency }
        assertEquals(freqs.sortedDescending(), freqs)
        val counts = db.rootClassCounts()
        assertEquals(all.size, counts.values.sum())
        for ((rootClass, n) in counts) {
            assertEquals(n, db.browseLexemes(rootClass, limit = 1000).size, rootClass)
        }
    }

    @Test
    fun `lexeme detail has ordered senses with placeholder decompositions`() {
        val lx = db.getLexeme(1)
        assertEquals("manu", lx?.phonForm)
        assertEquals("provisional", lx?.formStatus)
        val senses = db.sensesFor(1)
        assertTrue(senses.isNotEmpty())
        assertEquals(senses.map { it.senseNo }.sorted(), senses.map { it.senseNo })
        assertTrue(senses.all { it.primes.isEmpty() && it.decompStatus == "placeholder" })
        assertNull(db.getLexeme(-1))
    }

    @Test
    fun `lexeme without signs has none`() {
        assertTrue(db.signsFor(2).isEmpty())
    }

    @Test
    fun `search ignores case and surrounding space`() {
        assertEquals(db.searchLexemes("who").map { it.id }, db.searchLexemes("  WHO  ").map { it.id })
    }

    @Test
    fun `search matches a click form`() {
        assertEquals(listOf(15), db.searchLexemes("ʘa").map { it.id })
    }

    @Test
    fun `search and browse in an unknown root class are empty`() {
        assertTrue(db.searchLexemes("who", rootClass = "adjective").isEmpty())
        assertTrue(db.browseLexemes("adjective").isEmpty())
    }

    @Test
    fun `limits are respected`() {
        assertEquals(2, db.searchLexemes("", limit = 2).size)
        assertTrue(db.searchLexemes("", limit = 0).isEmpty())
        assertEquals(1, db.browseLexemes(limit = 1).size)
    }

    @Test
    fun `a lexeme with several matching senses appears once`() {
        val ids = db.searchLexemes("interrogative", limit = 100).map { it.id }
        assertEquals(ids.distinct(), ids)
    }

    @Test
    fun `unknown lexeme id has no senses or signs`() {
        assertTrue(db.sensesFor(-1).isEmpty())
        assertTrue(db.signsFor(-1).isEmpty())
    }
}
