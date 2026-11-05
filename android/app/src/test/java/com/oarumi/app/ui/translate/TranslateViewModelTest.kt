package com.oarumi.app.ui.translate

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.oarumi.app.data.audio.AndroidAudioSource
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import com.oarumi.app.data.packs.DirectoryBundledPacks
import com.oarumi.app.data.packs.PackRepository
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import oarumi.config.EngineConfig
import oarumi.db.LanguageStore
import oarumi.pipeline.Pipeline
import oarumi.reliability.AuditLog
import oarumi.renderers.AudioSource
import oarumi.renderers.SignRenderer
import oarumi.renderers.TactileRenderer
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class TranslateViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    private lateinit var db: AppDatabase
    private lateinit var store: LanguageStore
    private lateinit var pipeline: Pipeline
    private lateinit var audit: AuditLog

    @Before
    fun setUp() {
        val jvmDb = java.nio.file.Path.of("../../language/oarumi.db")
        assumeTrue("run ./scripts/bootstrap.sh", java.nio.file.Files.exists(jvmDb))

        kotlinx.coroutines.Dispatchers.setMain(dispatcher)

        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        db =
            Room.databaseBuilder(ctx, AppDatabase::class.java, "vm-test-oarumi.db")
                .createFromFile(java.io.File("../../language/oarumi.db"))
                .allowMainThreadQueries()
                .build()
        store = AndroidLanguageStore(db)

        val config =
            EngineConfig(
                home = java.nio.file.Path.of(ctx.filesDir.absolutePath),
                strictParity = false,
                devModels = false,
                offline = true,
                logLevel = "INFO",
            )
        pipeline = Pipeline(db = store, config = config)
        val audioDir = java.nio.file.Path.of("../../assets/audio")
        assumeTrue(
            "run tools/generate_audio_assets.py",
            java.nio.file.Files.exists(audioDir.resolve("manifest.json")),
        )
        val audioSource: AudioSource = AndroidAudioSource(ctx.assets)
        // The AndroidAudioSource only sees APK assets; batch 12 stages audio/.
        // For this test we skip renderers so the pipeline runs without them.
        val sign = SignRenderer(useExternal = false)
        val tactile = TactileRenderer()
        pipeline.registerRenderer("signed") { s -> sign.render(s).toJsonObject() }
        pipeline.registerRenderer("tactile") { s -> tactile.render(s).toJsonObject() }

        audit = AuditLog(java.nio.file.Path.of(ctx.filesDir.absolutePath, "audit.jsonl"))
    }

    @After
    fun tearDown() {
        db.close()
        kotlinx.coroutines.Dispatchers.resetMain()
    }

    @Test
    fun `translate success populates result`() =
        runTest(dispatcher) {
            val vm = TranslateViewModel(pipeline, audit, testPackRepository())
            vm.onInputChange("hola")
            vm.translate()
            val state = vm.state.first { !it.isTranslating }
            assertNotNull(state.result)
            assertEquals(false, state.isTranslating)
            assertTrue(state.statusMessage.startsWith("Translated"))
            assertTrue(state.formattedOutput.contains("hello"))
        }

    @Test
    fun `unknown language degrades`() =
        runTest(dispatcher) {
            val vm = TranslateViewModel(pipeline, audit, testPackRepository())
            vm.selectLanguage("xx")
            vm.onInputChange("hola")
            vm.translate()
            val state = vm.state.first { !it.isTranslating }
            assertNotNull(state.result)
            assertTrue(state.result!!.degraded)
            assertTrue(state.showDegraded)
        }

    @Test
    fun `blank input does not translate`() =
        runTest(dispatcher) {
            val vm = TranslateViewModel(pipeline, audit, testPackRepository())
            vm.onInputChange("   ")
            vm.translate()
            advanceUntilIdle()
            assertEquals(null, vm.state.value.result)
            assertTrue(vm.state.value.statusMessage.contains("Enter some text"))
        }
}

private fun testPackRepository(): PackRepository =
    PackRepository(
        java.nio.file.Files.createTempDirectory("packs-vm").toFile(),
        DirectoryBundledPacks(java.io.File("../../language/packs")),
    )
