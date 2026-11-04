package oarumi.renderers

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.Clitic
import oarumi.types.OarumiSurface
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TactileRendererTest {
    private fun surface(
        mood: String,
        phonemes: List<String>,
        cliticType: String,
    ): OarumiSurface =
        OarumiSurface(
            phonemes = phonemes,
            clitics = listOf(Clitic("=x", cliticType)),
            mood = mood,
            modality = "tactile",
        )

    @Test
    fun `decl selects T001`() {
        val out =
            TactileRenderer().render(
                surface("DECL", listOf("hello"), "mood_declarative"),
            )
        assertTrue(out.valid)
        assertEquals("T001", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `interr_where selects T002`() {
        val out =
            TactileRenderer().render(
                surface("INTERR", listOf("lonu", "bath"), "mood_interrogative"),
            )
        assertEquals("T002", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `interr_who selects T005`() {
        val out =
            TactileRenderer().render(
                surface("INTERR", listOf("who"), "mood_interrogative"),
            )
        assertEquals("T005", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `imper selects T004`() {
        val out =
            TactileRenderer().render(
                surface("IMPER", listOf("come"), "mood_imperative"),
            )
        assertEquals("T004", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `prom selects T003`() {
        val out =
            TactileRenderer().render(
                surface("PROM", listOf("i"), "mood_promissive"),
            )
        assertEquals("T003", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `express selects T005`() {
        val out =
            TactileRenderer().render(
                surface("EXPRESS", listOf("thanks"), "mood_expressive"),
            )
        assertEquals("T005", (protocolOf(out)["construction_id"] as JsonPrimitive).content)
    }

    @Test
    fun `referent is deterministic`() {
        val a = TactileRenderer().render(surface("DECL", listOf("hello"), "mood_declarative"))
        val b = TactileRenderer().render(surface("DECL", listOf("hello"), "mood_declarative"))
        assertEquals(
            (protocolOf(a)["referent_id"] as JsonPrimitive).content,
            (protocolOf(b)["referent_id"] as JsonPrimitive).content,
        )
    }

    @Test
    fun `referent id has correct shape`() {
        val out = TactileRenderer().render(surface("DECL", listOf("hello"), "mood_declarative"))
        val ref = (protocolOf(out)["referent_id"] as JsonPrimitive).content
        assertTrue(Regex("^r[0-9a-f]{8}$").matches(ref), "got: $ref")
    }

    private fun protocolOf(out: RenderOutput): JsonObject = out.payload["protocol"] as JsonObject
}
