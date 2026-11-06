package com.oarumi.app.ui.dictionary

import androidx.lifecycle.SavedStateHandle
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import com.oarumi.app.ui.nav.DictionaryEntryRoute
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.shadows.ShadowLooper
import java.io.File
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class DictionaryEntryViewModelTest {
    private lateinit var db: AppDatabase
    private lateinit var store: AndroidLanguageStore

    @Before
    fun setUp() {
        assumeTrue("run ./scripts/bootstrap.sh", Files.exists(Path.of("../../language/oarumi.db")))
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "entry-vm-test.db")
                .createFromFile(File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
        store = AndroidLanguageStore(db)
    }

    @After
    fun tearDown() = db.close()

    private fun loadedEntry(lexemeId: Int): EntryUiState {
        val vm = DictionaryEntryViewModel(store, SavedStateHandle(mapOf(DictionaryEntryRoute.ARG to lexemeId)))
        val deadline = System.currentTimeMillis() + 10_000
        while (!vm.state.value.loaded && System.currentTimeMillis() < deadline) {
            ShadowLooper.idleMainLooper()
            Thread.sleep(10)
        }
        return vm.state.value
    }

    @Test
    fun `entry shows the lexeme with its senses and signs`() {
        val state = loadedEntry(1)
        assertEquals("manu", state.lexeme?.phonForm)
        assertEquals(store.sensesFor(1).map { it.gloss }, state.senses.map { it.gloss })
        assertTrue(state.senses.isNotEmpty())
        assertEquals(store.signsFor(1).map { it.id }, state.signs.map { it.id })
    }

    @Test
    fun `unknown lexeme loads as absent`() {
        val state = loadedEntry(-1)
        assertTrue(state.loaded)
        assertNull(state.lexeme)
    }

    @Test
    fun `route path carries the lexeme id`() {
        assertEquals("dictionary/entry/7", DictionaryEntryRoute.path(7))
        assertEquals("dictionary/entry/{lexemeId}", DictionaryEntryRoute.PATTERN)
    }
}
