package oarumi.renderers

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.OarumiSurface
import java.nio.file.Files
import java.nio.file.Path

/**
 * Spoken renderer. Bit-identical to Python's TtsRenderer:
 *   - SSML string: byte-for-byte
 *   - phoneme_stream: identical
 *   - backend: "native" when a native backend produced audio, else "asset"
 *   - valid: false only on empty phoneme stream
 *
 * Routing rule (same as Python):
 *   any click or hum token  → asset backend (bundled WAVs)
 *   else                    → native backend if available, else asset
 */
class TtsRenderer(
    private val audio: AudioAssetLibrary,
    private val backend: TtsBackend? = null,
    private val tmpDir: Path = Files.createTempDirectory("oarumi-tts-"),
    private val modality: String = "spoken",
) {
    companion object {
        val CLICK_TOKENS: Set<String> =
            setOf(
                "ʘ", "ʘ̃", "ʘʰ",
                "ǀ", "ǀ̃", "ǀʰ",
                "ǃ", "ǃ̃", "ǃʰ",
                "ǁ", "ǁ̃", "ǁʰ",
                "ǂ", "ǂ̃", "ǂʰ",
            )
        val HUM_TOKENS: Set<String> =
            setOf(
                "hum_steady",
                "hum_pulsed",
                "hum_rising",
                "hum_falling",
            )

        private val CLICK_ASSET =
            mapOf(
                "ʘ" to "click_bilabial_plain", "ʘ̃" to "click_bilabial_nasal", "ʘʰ" to "click_bilabial_aspirated",
                "ǀ" to "click_dental_plain", "ǀ̃" to "click_dental_nasal", "ǀʰ" to "click_dental_aspirated",
                "ǃ" to "click_alveolar_plain", "ǃ̃" to "click_alveolar_nasal", "ǃʰ" to "click_alveolar_aspirated",
                "ǁ" to "click_lateral_plain", "ǁ̃" to "click_lateral_nasal", "ǁʰ" to "click_lateral_aspirated",
                "ǂ" to "click_palatal_plain", "ǂ̃" to "click_palatal_nasal", "ǂʰ" to "click_palatal_aspirated",
            )

        private val HUM_ASSET = HUM_TOKENS.associateWith { it }
    }

    fun render(surface: OarumiSurface): RenderOutput {
        val stream = surface.phonemes
        if (stream.isEmpty()) {
            return RenderOutput(
                modality = modality,
                payload =
                    mapOf(
                        "phoneme_stream" to JsonArray(emptyList()),
                        "audio_path" to JsonNull,
                    ),
                valid = false,
                errors = listOf("empty_phoneme_stream"),
            )
        }

        val hasSpecial = stream.any { it in CLICK_TOKENS || it in HUM_TOKENS }
        val nativeAvailable = !hasSpecial && backend?.isAvailable() == true
        val routing: String = if (nativeAvailable) "native" else "asset"

        val out = tmpDir.resolve("utterance-${stream.hashCode().toUInt().toString(16)}.wav")

        if (routing == "native") {
            val ssml = buildSsml(surface)
            val ok = backend!!.synthesize(ssml, out) && Files.exists(out)
            if (ok) {
                return successPayload(out, ssml = ssml, stream = stream, backendName = "native")
            }
            // Fall through to asset on failure.
        }

        assetSynthesize(stream, out)
        return successPayload(out, ssml = null, stream = stream, backendName = "asset")
    }

    fun buildSsml(surface: OarumiSurface): String {
        val body = surface.phonemes.joinToString(" ")
        val rate =
            when (surface.mood) {
                "DECL", "INTERR", "PROM", "EXPRESS" -> "medium"
                "IMPER" -> "fast"
                "VOC" -> "slow"
                else -> "medium"
            }
        return "<speak version=\"1.1\" xmlns=\"http://www.w3.org/2001/10/synthesis\" " +
            "xml:lang=\"en\"><prosody rate=\"$rate\">$body</prosody></speak>"
    }

    // --- internals ------------------------------------------------------

    private fun successPayload(
        out: Path,
        ssml: String?,
        stream: List<String>,
        backendName: String,
    ): RenderOutput {
        val payload = LinkedHashMap<String, JsonElement>()
        payload["audio_path"] = JsonPrimitive(out.toString())
        payload["ssml"] = if (ssml != null) JsonPrimitive(ssml) else JsonNull
        payload["phoneme_stream"] = JsonArray(stream.map { JsonPrimitive(it) })
        payload["backend"] = JsonPrimitive(backendName)
        payload["duration_ms"] = JsonPrimitive(WavWriter.durationMs(out))
        return RenderOutput(modality = modality, payload = payload, valid = true)
    }

    private fun assetSynthesize(
        stream: List<String>,
        out: Path,
    ) {
        val pcm = java.io.ByteArrayOutputStream()
        var sampleRate = audio.sampleRate
        for (token in stream) {
            val assetId: String? =
                when {
                    token in CLICK_TOKENS -> CLICK_ASSET[token]
                    token in HUM_TOKENS -> HUM_ASSET[token]
                    else -> null
                }
            if (assetId != null) {
                val asset = audio.get(assetId)
                val wav =
                    WavWriter.read(
                        Path.of("").resolve(asset.relPath).let {
                            // Asset bytes are read via the AudioSource abstraction:
                            // write to a temp file so WavWriter.read can parse the header.
                            val tmp = tmpDir.resolve("asset-${asset.id}.wav")
                            if (!Files.exists(tmp)) {
                                Files.createDirectories(tmp.parent)
                                Files.write(tmp, audio.readBytes(asset))
                            }
                            tmp
                        },
                    )
                sampleRate = wav.sampleRate
                pcm.write(wav.pcm)
            } else {
                pcm.write(WavWriter.toneSamples(token, sampleRate))
            }
        }
        WavWriter.write(out, sampleRate, pcm.toByteArray())
    }
}
