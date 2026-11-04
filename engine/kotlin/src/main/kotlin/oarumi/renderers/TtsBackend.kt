package oarumi.renderers

import java.nio.file.Path

/**
 * Abstraction over the platform's native TTS engine.
 *
 * The JVM has no default implementation; the Android module (Batch 10)
 * supplies one backed by android.speech.tts.TextToSpeech.
 *
 * For parity tests, pass `null` — the renderer then uses the deterministic
 * asset backend for every surface.
 */
interface TtsBackend {
    fun isAvailable(): Boolean

    /** Returns true on success. Writes a WAV at [outPath]. */
    fun synthesize(
        ssml: String,
        outPath: Path,
    ): Boolean
}
