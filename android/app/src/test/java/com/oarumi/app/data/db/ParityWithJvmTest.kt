package com.oarumi.app.data.db

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import oarumi.db.LanguageDb
import oarumi.types.OarumiJson
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.nio.file.Path
import kotlin.test.assertEquals

/**
 * Asserts that AndroidLanguageStore and LanguageDb return the same data
 * from the same SQLite file. This is the parity test Batch 13 refers to.
 */
@RunWith(RobolectricTestRunner::class)
class ParityWithJvmTest {
    private lateinit var jvm: LanguageDb
    private lateinit var db: AppDatabase
    private lateinit var android: AndroidLanguageStore

    @Before
    fun setUp() {
        val jvmDbPath = Path.of("../../language/oarumi.db")
        org.junit.Assume.assumeTrue(
            "language/oarumi.db missing; run ./scripts/bootstrap.sh",
            java.nio.file.Files.exists(jvmDbPath),
        )
        jvm = LanguageDb(jvmDbPath)

        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "test-parity.db")
                .createFromFile(java.io.File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
        android = AndroidLanguageStore(db)
    }

    @After
    fun tearDown() {
        db.close()
        jvm.close()
    }

    @Test
    fun `prime sets are identical`() {
        val jvmPrimes = jvm.allPrimes().associateBy { it.id }
        val androidPrimes = android.allPrimes().associateBy { it.id }
        assertEquals(jvmPrimes.keys, androidPrimes.keys)
        for (id in jvmPrimes.keys) {
            val a = jvmPrimes[id]!!
            val b = androidPrimes[id]!!
            assertEquals(a.gloss, b.gloss, "gloss for $id")
            assertEquals(a.category, b.category, "category for $id")
            assertEquals(a.combinators, b.combinators, "combinators for $id")
            assertEquals(a.spokenForm, b.spokenForm, "spoken_form for $id")
            assertEquals(a.signedForm, b.signedForm, "signed_form for $id")
            assertEquals(a.tactileForm, b.tactileForm, "tactile_form for $id")
        }
    }

    @Test
    fun `lexeme search is identical`() {
        for (q in listOf("who", "manu", "hello", "x")) {
            val j = jvm.searchLexemes(q, limit = 50).map { it.phonForm }
            val a = android.searchLexemes(q, limit = 50).map { it.phonForm }
            assertEquals(j, a, "search '$q'")
        }
    }

    @Test
    fun `get_by_phon is identical`() {
        for (phon in listOf("manu", "tinu", "ke", "si")) {
            val j = jvm.getLexemeByPhon(phon)
            val a = android.getLexemeByPhon(phon)
            assertEquals(j?.id, a?.id, "phon '$phon'")
            assertEquals(j?.gloss, a?.gloss, "gloss '$phon'")
        }
    }

    @Suppress("unused")
    private val json = OarumiJson
}
