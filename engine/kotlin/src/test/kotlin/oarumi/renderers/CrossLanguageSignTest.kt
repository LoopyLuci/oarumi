package oarumi.renderers

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
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

class CrossLanguageSignTest {
    private val fixturesDir: Path =
        Path.of(System.getProperty("oarumi.parity.data") ?: "../tests/parity/data")
            .resolve("renderers/sign")

    private val goldDir: Path = fixturesDir.resolve("gold")

    @Test
    fun `kotlin sign output matches frozen gold`() {
        assumeTrue(Files.exists(fixturesDir.resolve("cases.json")), "no sign fixtures")
        assumeTrue(Files.exists(goldDir), "no gold dir — run the Python freeze step first")

        val renderer = SignRenderer()
        val cases =
            Json.parseToJsonElement(
                fixturesDir.resolve("cases.json").readText(),
            ).jsonObject["cases"]!!.jsonArray

        for (caseElem in cases) {
            val case = caseElem.jsonObject
            val id = case["id"]!!.jsonPrimitive.content
            val gloss = case["gloss"]!!.jsonPrimitive.content
            val annot =
                case["annotation"]?.let {
                    if (it is JsonNull) null else it.jsonPrimitive.content
                }

            val surface =
                OarumiSurface(
                    phonemes = listOf(gloss),
                    clitics = listOf(Clitic("=ha", "mood_declarative")),
                    mood = "DECL",
                    modality = "signed",
                )
            val got = renderer.render(surface, hamnosys = annot, gloss = gloss).toJsonObject()

            val goldFile = goldDir.resolve("$id.json")
            assumeTrue(Files.exists(goldFile), "no gold for $id")

            val expected = Json.parseToJsonElement(goldFile.readText())
            assertEquals(expected, got, "case=$id")
        }
    }

    @Suppress("unused")
    private fun unusedElem(e: JsonElement) = e
}
