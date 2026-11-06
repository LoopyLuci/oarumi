package com.oarumi.app.ui.learn

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.shadows.ShadowLooper
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class LearnViewModelTest {
    private lateinit var db: AppDatabase

    @Before
    fun setUp() {
        val jvmDb = java.nio.file.Path.of("../../language/oarumi.db")
        assumeTrue("run ./scripts/bootstrap.sh", java.nio.file.Files.exists(jvmDb))
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "learn-test.db")
                .createFromFile(java.io.File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
    }

    @After
    fun tearDown() = db.close()

    /** The primes load on a background thread, so wait for them before the test reads state. */
    private fun loadedViewModel(): LearnViewModel {
        val vm = LearnViewModel(AndroidLanguageStore(db))
        val deadline = System.currentTimeMillis() + 10_000
        while (vm.state.value.primes.isEmpty() && System.currentTimeMillis() < deadline) {
            ShadowLooper.idleMainLooper()
            Thread.sleep(10)
        }
        return vm
    }

    @Test
    fun `next wraps around`() {
        val vm = loadedViewModel()
        val size = vm.state.value.primes.size
        assertTrue(size > 0)
        repeat(size) { vm.next() }
        assertEquals(0, vm.state.value.index)
    }

    @Test
    fun `previous wraps around`() {
        val vm = loadedViewModel()
        vm.previous()
        assertEquals(vm.state.value.primes.size - 1, vm.state.value.index)
    }

    @Test
    fun `current is populated`() {
        val vm = loadedViewModel()
        assertNotNull(vm.state.value.current)
    }
}
