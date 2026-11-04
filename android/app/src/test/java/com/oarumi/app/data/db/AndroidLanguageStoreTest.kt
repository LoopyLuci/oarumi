package com.oarumi.app.data.db

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class AndroidLanguageStoreTest {
    private lateinit var db: AppDatabase
    private lateinit var store: AndroidLanguageStore

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        // Use the packaged asset DB the same way the app does.
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "test-oarumi.db")
                .createFromFile(java.io.File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
        store = AndroidLanguageStore(db)
    }

    @After
    fun tearDown() {
        db.close()
    }

    @Test
    fun `all primes loaded and match count`() {
        val primes = store.allPrimes()
        assertTrue(primes.size >= 60, "expected >= 60 primes, got ${primes.size}")
    }

    @Test
    fun `get prime by id`() {
        val p = store.getPrime("WANT")
        assertNotNull(p)
        assertEquals("WANT", p.id)
        assertTrue(p.spokenForm.isNotBlank())
    }

    @Test
    fun `missing prime returns null`() {
        assertNull(store.getPrime("NOT_A_PRIME"))
    }

    @Test
    fun `search lexemes`() {
        val hits = store.searchLexemes("who", limit = 10)
        assertTrue(hits.isNotEmpty(), "expected hits for 'who'")
        assertTrue(hits.first().frequency > 0)
    }

    @Test
    fun `lexeme by phon`() {
        val lx = store.getLexemeByPhon("manu")
        assertNotNull(lx)
        assertEquals("manu", lx.phonForm)
    }
}
