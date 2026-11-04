package com.oarumi.app.data.tts

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import kotlinx.coroutines.suspendCancellableCoroutine
import oarumi.renderers.TtsBackend
import java.io.File
import java.nio.file.Path
import java.util.Locale
import java.util.UUID
import kotlin.coroutines.resume

/**
 * TtsBackend implementation using android.speech.tts.TextToSpeech.
 *
 * Important: TTS initialization is asynchronous and can fail (missing engine,
 * no offline voices). The renderer treats isAvailable() == false as "use the
 * asset backend", which is deterministic and always works.
 *
 * synthesizeToFile() respects SSML when the engine supports it. The asset
 * backend (TtsRenderer.assetSynthesize) handles clicks and hums, so this class
 * is only ever asked to render plain phoneme streams.
 */
class AndroidTtsBackend(context: Context) : TtsBackend, AutoCloseable {
    private val appContext = context.applicationContext
    private var engine: TextToSpeech? = null

    @Volatile private var ready = false

    @Volatile private var failed = false
    private val initLock = Object()

    init {
        startInit()
    }

    private fun startInit() {
        engine =
            TextToSpeech(appContext) { status ->
                synchronized(initLock) {
                    ready = status == TextToSpeech.SUCCESS &&
                        engine?.setLanguage(Locale.ENGLISH) != TextToSpeech.LANG_MISSING_DATA &&
                        engine?.setLanguage(Locale.ENGLISH) != TextToSpeech.LANG_NOT_SUPPORTED
                    failed = !ready
                }
            }
    }

    /** Waits up to 2 s for engine init. Called once at app startup; safe to re-call. */
    suspend fun awaitReady(timeoutMs: Long = 2_000L): Boolean {
        if (ready) return true
        if (failed) return false
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            synchronized(initLock) { if (ready || failed) return ready }
            kotlinx.coroutines.delay(20)
        }
        synchronized(initLock) { failed = true }
        return false
    }

    override fun isAvailable(): Boolean = ready && !failed

    override fun synthesize(
        ssml: String,
        outPath: Path,
    ): Boolean {
        val e = engine ?: return false
        if (!isAvailable()) return false
        val target = File(outPath.toString())
        target.parentFile?.mkdirs()

        val token = "oarumi-" + UUID.randomUUID()

        // Block until the utterance completes or fails. The caller (TtsRenderer)
        // is on a background dispatcher; blocking here is acceptable and
        // simplifies the renderer's contract.
        val done = java.util.concurrent.CountDownLatch(1)
        val success = java.util.concurrent.atomic.AtomicBoolean(false)

        e.setOnUtteranceProgressListener(
            object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}

                override fun onDone(utteranceId: String?) {
                    if (utteranceId == token) {
                        success.set(true)
                        done.countDown()
                    }
                }

                @Deprecated("Deprecated in API 21; required override")
                override fun onError(utteranceId: String?) {
                    if (utteranceId == token) {
                        success.set(false)
                        done.countDown()
                    }
                }

                override fun onError(
                    utteranceId: String?,
                    errorCode: Int,
                ) {
                    if (utteranceId == token) {
                        success.set(false)
                        done.countDown()
                    }
                }
            },
        )

        val result = e.synthesizeToFile(ssml, null, target, token)
        if (result != TextToSpeech.SUCCESS) return false

        val ok = done.await(30, java.util.concurrent.TimeUnit.SECONDS)
        return ok && success.get() && target.exists() && target.length() > 44
    }

    override fun close() {
        engine?.stop()
        engine?.shutdown()
        engine = null
        ready = false
    }

    @Suppress("unused")
    private suspend fun unusedSuspend(cb: suspend () -> Unit) =
        suspendCancellableCoroutine<Unit> { cont -> cont.resume(Unit) }
}
