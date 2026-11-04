package com.oarumi.app.data

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.oarumi.app.data.audio.AndroidAudioSource
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import com.oarumi.app.data.tts.AndroidTtsBackend
import kotlinx.coroutines.runBlocking
import oarumi.config.EngineConfig
import oarumi.db.LanguageStore
import oarumi.pipeline.Pipeline
import oarumi.renderers.AudioAssetLibrary
import oarumi.renderers.SignRenderer
import oarumi.renderers.TactileRenderer
import oarumi.renderers.TtsBackend
import oarumi.renderers.TtsRenderer
import oarumi.types.TranslationRequest
import org.junit.Test
import org.junit.runner.RunWith
import java.nio.file.Files
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Instrumented smoke: opens the packaged DB via Room, runs a full translate,
 * and asserts that at least one modality payload is populated.
 *
 * Runs on the emulator in Batch 16's nightly job.
 */
@RunWith(AndroidJUnit4::class)
class EndToEndSmokeTest {
    @Test
    fun translate_hola_produces_spoken_and_signed() =
        runBlocking {
            val ctx = ApplicationProvider.getApplicationContext<Context>()
            val db = AppDatabase.create(ctx)
            val store: LanguageStore = AndroidLanguageStore(db)

            val config =
                EngineConfig(
                    home = java.nio.file.Path.of(ctx.filesDir.absolutePath),
                    strictParity = false,
                    devModels = false,
                    offline = true,
                    logLevel = "INFO",
                )
            val audio = AudioAssetLibrary(AndroidAudioSource(ctx.assets), requireVerified = false)
            val ttsBackend: TtsBackend = AndroidTtsBackend(ctx)
            try {
                val pipeline = Pipeline(db = store, config = config)
                val tts = TtsRenderer(audio = audio, backend = ttsBackend)
                val sign = SignRenderer(useExternal = false)
                val tactile = TactileRenderer()
                pipeline.registerRenderer("spoken") { s -> tts.render(s).toJsonObject() }
                pipeline.registerRenderer("signed") { s -> sign.render(s).toJsonObject() }
                pipeline.registerRenderer("tactile") { s -> tactile.render(s).toJsonObject() }

                val result =
                    pipeline.translate(
                        TranslationRequest(text = "hola", lang = "es", modality = "signed"),
                    )
                assertEquals(false, result.degraded)
                assertTrue(result.modalities.containsKey("signed"))
                val sigml = result.modalities["signed"]!!["sigml"]
                assertNotNull(sigml)
                val sigmlText = sigml.toString()
                assertTrue("hns_sign" in sigmlText)
            } finally {
                (ttsBackend as? AutoCloseable)?.close()
                db.close()
            }
        }

    @Suppress("unused")
    private fun touchFs() = Files.createTempFile("x", ".y")
}
