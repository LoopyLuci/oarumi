package oarumi.renderers

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
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

class CrossLanguageTactileTest {
    private val fixturesDir: Path =
        Path.of(System.getProperty("oarumi.parity.data") ?: "../tests/parity/data")
            .resolve("renderers/tactile")

    @Test
    fun `kotlin tactile output matches frozen gold`() {
        assumeTrue(Files.exists(fixturesDir.resolve("cases.json")), "no tactile fixtures")
        val goldDir = fixturesDir.resolve("gold")
        assumeTrue(Files.exists(goldDir), "no gold dir")

        val renderer = TactileRenderer()
        val cases =
            Json.parseToJsonElement(
                fixturesDir.resolve("cases.json").readText(),
            ).jsonObject["cases"]!!.jsonArray

        for (caseElem in cases) {
            val case = caseElem.jsonObject
            val id = case["id"]!!.jsonPrimitive.content
            val sObj = case["surface"]!!.jsonObject
            val surface =
                OarumiSurface(
                    phonemes = sObj["phonemes"]!!.jsonArray.map { it.jsonPrimitive.content },
                    clitics =
                        sObj["clitics"]!!.jsonArray.map {
                            val c = it.jsonObject
                            Clitic(
                                form = c["form"]!!.jsonPrimitive.content,
                                type = c["type"]!!.jsonPrimitive.content,
                            )
                        },
                    mood = sObj["mood"]!!.jsonPrimitive.content,
                    modality = sObj["modality"]!!.jsonPrimitive.content,
                )
            val got = renderer.render(surface).toJsonObject()

            val goldFile = goldDir.resolve("$id.json")
            assumeTrue(Files.exists(goldFile), "no gold for $id")

            val expected = Json.parseToJsonElement(goldFile.readText())
            assertEquals(expected, got, "case=$id")
        }
    }

    @Suppress("unused")
    private fun unusedObj(o: JsonObject) = o
}
