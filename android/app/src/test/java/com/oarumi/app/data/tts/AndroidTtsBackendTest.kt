package com.oarumi.app.data.tts

import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.test.runTest
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class AndroidTtsBackendTest {
    @Test
    fun `initialises and reports availability`() =
        runTest {
            val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
            val backend = AndroidTtsBackend(ctx)
            try {
                val ready = backend.awaitReady(timeoutMs = 500)
                // Robolectric may or may not provide a functional TTS engine; the
                // contract is that isAvailable() reflects actual state.
                assertTrue(ready == backend.isAvailable())
            } finally {
                backend.close()
            }
        }

    @Test
    fun `synthesize returns false when engine unavailable`() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val backend = AndroidTtsBackend(ctx)
        try {
            if (backend.isAvailable()) return // skip when engine is functional
            val out = java.nio.file.Files.createTempFile("tts-", ".wav")
            assertFalse(backend.synthesize("<speak>x</speak>", out))
        } finally {
            backend.close()
        }
    }

    @Suppress("unused")
    private fun touch(v: Any?) = assertNotNull(v)
}
