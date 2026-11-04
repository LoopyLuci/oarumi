package oarumi.renderers

import oarumi.types.Clitic
import oarumi.types.OarumiSurface
import org.junit.jupiter.api.Assumptions.assumeTrue
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class TtsRendererTest {
    private val assetDir: Path =
        Path.of(System.getProperty("user.dir")).resolve("../../assets/audio").normalize()

    private fun renderer(): TtsRenderer {
        assumeTrue(
            Files.exists(assetDir.resolve("manifest.json")),
            "run tools/generate_audio_assets.py first",
        )
        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        return TtsRenderer(audio = lib, backend = null)
    }

    private fun surface(
        vararg phonemes: String,
        mood: String = "DECL",
    ): OarumiSurface =
        OarumiSurface(
            phonemes = phonemes.toList(),
            clitics = listOf(Clitic("=ha", "mood_declarative")),
            mood = mood,
            modality = "spoken",
        )

    @Test
    fun `click routes to asset backend and produces a playable wav`() {
        val r = renderer()
        val out = r.render(surface("ʘ", "a"))
        assertTrue(out.valid, "expected valid, errors=${out.errors}")
        assertEquals("asset", (out.payload["backend"] as kotlinx.serialization.json.JsonPrimitive).content)
        val path = Path.of((out.payload["audio_path"] as kotlinx.serialization.json.JsonPrimitive).content)
        assertTrue(Files.exists(path))
        assertTrue(Files.size(path) > 44) // header + samples
        val dur = WavWriter.durationMs(path)
        assertTrue(dur > 0)
    }

    @Test
    fun `hum routes to asset backend`() {
        val r = renderer()
        val out = r.render(surface("hum_rising", "hello"))
        assertTrue(out.valid)
        assertEquals("asset", (out.payload["backend"] as kotlinx.serialization.json.JsonPrimitive).content)
    }

    @Test
    fun `plain falls back to asset when no native backend`() {
        val r = renderer()
        val out = r.render(surface("hello"))
        assertTrue(out.valid)
        assertEquals("asset", (out.payload["backend"] as kotlinx.serialization.json.JsonPrimitive).content)
    }

    @Test
    fun `empty surface is invalid`() {
        val r = renderer()
        val out = r.render(surface())
        assertEquals(false, out.valid)
        assertTrue("empty_phoneme_stream" in out.errors)
    }

    @Test
    fun `ssml shape matches python`() {
        val r = renderer()
        val ssml = r.buildSsml(surface("hello", mood = "INTERR"))
        assertEquals(
            "<speak version=\"1.1\" xmlns=\"http://www.w3.org/2001/10/synthesis\" " +
                "xml:lang=\"en\"><prosody rate=\"medium\">hello</prosody></speak>",
            ssml,
        )
    }

    @Test
    fun `ssml rate for imper is fast`() {
        val r = renderer()
        val ssml = r.buildSsml(surface("come", mood = "IMPER"))
        assertTrue("rate=\"fast\"" in ssml)
    }

    @Test
    fun `ssml rate for voc is slow`() {
        val r = renderer()
        val ssml = r.buildSsml(surface("you", mood = "VOC"))
        assertTrue("rate=\"slow\"" in ssml)
    }

    @Test
    fun `no native backend means ssml is null`() {
        val r = renderer()
        val out = r.render(surface("ʘ", "a"))
        assertNull(out.payload["ssml"]?.let { if (it is kotlinx.serialization.json.JsonNull) null else it })
    }

    @Test
    fun `fake native backend is used for plain surfaces`() {
        val fake =
            object : TtsBackend {
                override fun isAvailable() = true

                override fun synthesize(
                    ssml: String,
                    outPath: Path,
                ): Boolean {
                    WavWriter.write(outPath, 22050, ByteArray(4000))
                    return true
                }
            }
        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        val r = TtsRenderer(audio = lib, backend = fake)
        val out = r.render(surface("hello"))
        assertEquals("native", (out.payload["backend"] as kotlinx.serialization.json.JsonPrimitive).content)
        assertNotNull(out.payload["ssml"])
    }
}
