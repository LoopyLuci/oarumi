package com.oarumi.app.ui.dictionary

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import oarumi.db.Prime
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
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class DictionaryViewModelTest {
    private lateinit var db: AppDatabase
    private lateinit var store: AndroidLanguageStore

    @Before
    fun setUp() {
        assumeTrue("run ./scripts/bootstrap.sh", Files.exists(Path.of("../../language/oarumi.db")))
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "dictionary-vm-test.db")
                .createFromFile(File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
        store = AndroidLanguageStore(db)
    }

    @After
    fun tearDown() = db.close()

    /** Work on the view model runs on background threads, so wait for a state before asserting. */
    private fun awaitState(
        vm: DictionaryViewModel,
        ready: (DictionaryUiState) -> Boolean,
    ): DictionaryUiState {
        val deadline = System.currentTimeMillis() + 10_000
        while (!ready(vm.state.value) && System.currentTimeMillis() < deadline) {
            ShadowLooper.idleMainLooper()
            Thread.sleep(10)
        }
        assertTrue(ready(vm.state.value), "state never became ready")
        return vm.state.value
    }

    @Test
    fun `blank query browses every lexeme by frequency`() {
        val vm = DictionaryViewModel(store)
        val state = awaitState(vm) { it.results.isNotEmpty() && it.primes.isNotEmpty() }
        assertEquals(store.browseLexemes(limit = 500).map { it.id }, state.results.map { it.id })
        val freqs = state.results.map { it.frequency }
        assertEquals(freqs.sortedDescending(), freqs)
    }

    @Test
    fun `filter browses one root class`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        val nouns = store.browseLexemes("noun", limit = 500)
        vm.onFilterChange(DictionaryFilter.Nouns)
        val state = awaitState(vm) { it.filter == DictionaryFilter.Nouns && it.results.size == nouns.size }
        assertTrue(state.results.all { it.rootClass == "noun" })
    }

    @Test
    fun `query finds a word by its sense gloss`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        vm.onQueryChange("interrogative person")
        val state = awaitState(vm) { s -> s.query == "interrogative person" && s.results.any { it.phonForm == "manu" } }
        assertTrue(state.results.isNotEmpty())
    }

    @Test
    fun `a wildcard in the query matches nothing`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        vm.onQueryChange("%")
        awaitState(vm) { it.query == "%" && it.results.isEmpty() }
    }

    @Test
    fun `primes filter shows the inventory instead of lexemes`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.primes.isNotEmpty() }
        vm.onFilterChange(DictionaryFilter.Primes)
        val state = awaitState(vm) { it.filter == DictionaryFilter.Primes && it.visiblePrimes.isNotEmpty() }
        assertTrue(state.results.isEmpty())
        assertEquals(state.primes.size, state.visiblePrimes.size)
    }

    private fun prime(
        id: String,
        gloss: String,
        spoken: String,
    ) = Prime(
        id = id,
        gloss = gloss,
        category = "substantives",
        combinators = listOf("substance"),
        spokenForm = spoken,
        signedForm = "sign:$id",
        tactileForm = "tac:$id",
        nsmVersion = "test",
    )

    @Test
    fun `prime matching is case-insensitive over id, gloss and spoken form`() {
        val primes = listOf(prime("SOMEONE", "someone", "sa-mo"), prime("BODY", "body", "bodi"))
        assertEquals(listOf("SOMEONE"), matchPrimes(primes, "someone").map { it.id })
        assertEquals(listOf("BODY"), matchPrimes(primes, "BOD").map { it.id })
        assertEquals(listOf("SOMEONE"), matchPrimes(primes, "sa-mo").map { it.id })
        assertEquals(primes, matchPrimes(primes, "   "))
    }

    @Test
    fun `surrounding space in the query is ignored`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        vm.onQueryChange("  who  ")
        val state = awaitState(vm) { it.query == "  who  " && it.results.firstOrNull()?.phonForm == "manu" }
        assertTrue(state.results.isNotEmpty())
    }

    @Test
    fun `a newer query replaces the results of an older one`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        vm.onQueryChange("interrogative")
        vm.onQueryChange("who")
        val state = awaitState(vm) { it.query == "who" && it.results.isNotEmpty() && it.results.size == 1 }
        assertEquals(listOf("manu"), state.results.map { it.phonForm })
    }

    @Test
    fun `a query that matches nothing in one class shows no words`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.results.isNotEmpty() }
        vm.onFilterChange(DictionaryFilter.Nouns)
        awaitState(vm) { it.filter == DictionaryFilter.Nouns && it.results.size == 2 }
        vm.onQueryChange("particle-only-word")
        awaitState(vm) { it.query == "particle-only-word" && it.results.isEmpty() }
    }

    @Test
    fun `a query that matches no prime shows none under the primes filter`() {
        val vm = DictionaryViewModel(store)
        awaitState(vm) { it.primes.isNotEmpty() }
        vm.onFilterChange(DictionaryFilter.Primes)
        vm.onQueryChange("zzz-no-such-prime")
        val state = awaitState(vm) { it.query == "zzz-no-such-prime" && it.visiblePrimes.isEmpty() }
        assertTrue(state.results.isEmpty())
    }
}
