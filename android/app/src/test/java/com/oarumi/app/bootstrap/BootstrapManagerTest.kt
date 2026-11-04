package com.oarumi.app.bootstrap

import androidx.test.core.app.ApplicationProvider
import com.oarumi.app.data.mlkit.MlKitTranslator
import com.oarumi.app.data.pivot.FlavorPivot
import com.oarumi.app.data.tts.AndroidTtsBackend
import kotlinx.coroutines.test.runTest
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.assertFalse
import kotlin.test.assertTrue

@RunWith(RobolectricTestRunner::class)
class BootstrapManagerTest {
    /** Fake MlKitTranslator that marks everything as ready without downloading. */
    private class FakeMlKit(private val succeed: Boolean = true) : MlKitTranslator {
        override fun supportedLanguages() = setOf("es", "fr", "de", "zh", "ar", "en")

        override suspend fun isDownloaded(sourceLang: String) = succeed

        override suspend fun ensureModel(sourceLang: String) = succeed

        override suspend fun translate(
            text: String,
            sourceLang: String,
            offline: Boolean,
        ) = text

        override fun close() = Unit
    }

    @Test
    fun `startBootstrap marks selected languages ready`() =
        runTest {
            val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
            val store = BootstrapStateStore()
            val tts = AndroidTtsBackend(ctx)
            try {
                val manager = BootstrapManager(ctx, store, tts, FakeMlKit())
                manager.isReady()
                store.toggleLanguage("fr")
                val ok = manager.startBootstrap()
                assertTrue(ok, "expected ready, state=${store.state.value}")
                val selected = store.state.value.languages.filter { it.code in store.state.value.selectedLanguages }
                assertTrue(selected.isNotEmpty() && selected.all { it.state == AssetState.READY })
            } finally {
                tts.close()
            }
        }

    @Test
    fun `failed download marks asset failed and not ready`() =
        runTest {
            // Downloads only exist in the mlkit flavor.
            if (!FlavorPivot.hasMlKit) return@runTest
            val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
            val store = BootstrapStateStore()
            val tts = AndroidTtsBackend(ctx)
            try {
                val manager = BootstrapManager(ctx, store, tts, FakeMlKit(succeed = false))
                manager.isReady()
                val ok = manager.startBootstrap()
                assertFalse(ok)
                assertTrue(store.state.value.languages.any { it.state == AssetState.FAILED })
            } finally {
                tts.close()
            }
        }

    @Test
    fun `argos flavor is ready without downloads`() =
        runTest {
            // Only testable when running the argos flavor. Skip otherwise.
            if (FlavorPivot.hasMlKit) return@runTest
            val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
            val store = BootstrapStateStore()
            val tts = AndroidTtsBackend(ctx)
            try {
                val manager = BootstrapManager(ctx, store, tts, null)
                val ok = manager.startBootstrap()
                assertTrue(ok)
                assertTrue(store.state.value.languages.all { it.state == AssetState.READY })
            } finally {
                tts.close()
            }
        }
}
