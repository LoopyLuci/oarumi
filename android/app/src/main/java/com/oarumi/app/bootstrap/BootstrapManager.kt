package com.oarumi.app.bootstrap

import android.content.Context
import android.content.Intent
import android.speech.tts.TextToSpeech
import com.oarumi.app.data.pivot.FlavorPivot
import com.oarumi.app.data.tts.AndroidTtsBackend
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Orchestrates bootstrap: ML Kit model downloads (mlkit flavor only) and
 * TTS availability check (both flavors).
 *
 * Lives at app scope (Singleton); writes to BootstrapStateStore so the
 * Compose wizard can observe progress.
 */
@Singleton
class BootstrapManager
    @Inject
    constructor(
        @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
        private val stateStore: BootstrapStateStore,
        private val ttsBackend: AndroidTtsBackend,
        private val mlKit: com.oarumi.app.data.mlkit.MlKitTranslator?,
    ) {
        /** True if every selected language and TTS are ready. Idempotent; safe to call on startup. */
        suspend fun isReady(): Boolean =
            withContext(Dispatchers.IO) {
                stateStore.initialise(
                    flavor = FlavorPivot.name,
                    availableLanguages = availableLanguages(),
                )
                if (!FlavorPivot.hasMlKit) {
                    // Phrasebook flavor: everything is bundled.
                    stateStore.recomputeReadiness()
                    return@withContext true
                }
                val current = stateStore.state.value
                for (code in current.selectedLanguages) {
                    val downloaded = mlKit?.isDownloaded(code) == true
                    stateStore.setLanguageState(
                        code,
                        if (downloaded) AssetState.READY else AssetState.NOT_STARTED,
                    )
                }
                val ttsOk = ttsBackend.awaitReady(timeoutMs = 500)
                stateStore.setTts(if (ttsOk) AssetState.READY else AssetState.FAILED, ttsOk)
                stateStore.recomputeReadiness()
                return@withContext stateStore.state.value.ready
            }

        /** Available source languages in this flavor. */
        fun availableLanguages(): List<String> =
            if (FlavorPivot.hasMlKit) listOf("es", "fr", "de", "zh", "ar") else listOf("es", "fr", "de", "zh", "ar")

        /** Kick off downloads for the currently selected languages. */
        suspend fun startBootstrap(): Boolean =
            withContext(Dispatchers.IO) {
                // The background worker can run before isReady(); initialise so the selection is populated.
                stateStore.initialise(flavor = FlavorPivot.name, availableLanguages = availableLanguages())
                stateStore.setError(null)
                stateStore.setInProgress(true)
                try {
                    if (FlavorPivot.hasMlKit) {
                        val current = stateStore.state.value
                        for (code in current.selectedLanguages) {
                            stateStore.setLanguageState(code, AssetState.DOWNLOADING, progress = -1f)
                            val ok = mlKit?.ensureModel(code) == true
                            stateStore.setLanguageState(
                                code,
                                if (ok) AssetState.READY else AssetState.FAILED,
                                progress = if (ok) 1f else 0f,
                                error = if (ok) null else "download_failed",
                            )
                        }
                    } else {
                        // No downloads; mark everything ready.
                        stateStore.state.value.languages.forEach { lang ->
                            stateStore.setLanguageState(lang.code, AssetState.READY, progress = 1f)
                        }
                    }

                    // TTS is optional; mark READY if available, FAILED (non-fatal) otherwise.
                    val ttsOk = ttsBackend.awaitReady(timeoutMs = 1000)
                    stateStore.setTts(if (ttsOk) AssetState.READY else AssetState.FAILED, ttsOk)

                    stateStore.recomputeReadiness()
                    stateStore.state.value.ready
                } catch (e: Exception) {
                    stateStore.setError(e.message ?: "Unknown error")
                    false
                } finally {
                    stateStore.setInProgress(false)
                }
            }

        /** Opens the system TTS-data installer for languages where the voice is missing. */
        fun openTtsInstaller() {
            val intent =
                Intent(TextToSpeech.Engine.ACTION_INSTALL_TTS_DATA).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            runCatching { context.startActivity(intent) }
        }

        @Suppress("unused")
        private fun localeFor(code: String): Locale = Locale.forLanguageTag(code)
    }
