package oarumi.renderers

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import oarumi.types.Clitic
import oarumi.types.OarumiSurface
import org.junit.jupiter.api.Assumptions.assumeTrue
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.readText
import kotlin.test.Test
import kotlin.test.assertEquals

class CrossLanguageTtsTest {
    private val fixturesDir: Path =
        Path.of(System.getProperty("oarumi.parity.data") ?: "../tests/parity/data")
            .resolve("renderers/tts")

    private val assetDir: Path =
        Path.of(System.getProperty("user.dir")).resolve("../../assets/audio").normalize()

    @Test
    fun `kotlin tts output matches frozen gold`() {
        assumeTrue(Files.exists(fixturesDir.resolve("cases.json")), "no tts fixtures")
        assumeTrue(Files.exists(assetDir.resolve("manifest.json")), "run generate_audio_assets.py")

        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        val renderer = TtsRenderer(audio = lib, backend = null)

        val cases =
            Json.parseToJsonElement(
                fixturesDir.resolve("cases.json").readText(),
            ).jsonObject["cases"]!!.jsonArray

        for (caseElem in cases) {
            val case = caseElem.jsonObject
            val id = case["id"]!!.jsonPrimitive.content
            val surface = surfaceFromJson(case["surface"]!!.jsonObject)
            val got = renderer.render(surface).toJsonObject()

            val goldFile = fixturesDir.resolve("gold").resolve("$id.json")
            assumeTrue(
                Files.exists(goldFile),
                "no gold for $id — run the Python freeze step first",
            )

            val expected = Json.parseToJsonElement(goldFile.readText()).jsonObject
            val gotCanonical = canonical(got)
            val expectedCanonical = canonical(expected)
            assertEquals(expectedCanonical, gotCanonical, "case=$id")
        }
    }

    private fun surfaceFromJson(obj: JsonObject): OarumiSurface {
        return OarumiSurface(
            phonemes = obj["phonemes"]!!.jsonArray.map { it.jsonPrimitive.content },
            clitics =
                obj["clitics"]!!.jsonArray.map {
                    val c = it.jsonObject
                    Clitic(
                        form = c["form"]!!.jsonPrimitive.content,
                        type = c["type"]!!.jsonPrimitive.content,
                    )
                },
            mood = obj["mood"]!!.jsonPrimitive.content,
            modality = obj["modality"]!!.jsonPrimitive.content,
        )
    }

    private fun canonical(elem: JsonElement): JsonElement {
        val obj = elem.jsonObject.toMutableMap()
        obj.remove("audio_path")
        obj.remove("duration_ms")
        obj["backend"]?.let {
            val s = it.jsonPrimitive.content
            if (s in setOf("espeak", "android", "native")) {
                obj["backend"] = JsonPrimitive("native")
            }
        }
        return JsonObject(obj)
    }

    @Suppress("unused")
    private fun unusedJsonNull(n: JsonNull) = n
}
