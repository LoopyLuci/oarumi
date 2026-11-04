package oarumi.renderers

import oarumi.types.Clitic
import oarumi.types.OarumiSurface
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SignRendererTest {
    private fun surface(): OarumiSurface =
        OarumiSurface(
            phonemes = listOf("manu"),
            clitics = listOf(Clitic("=ha", "mood_declarative")),
            mood = "DECL",
            modality = "signed",
        )

    @Test
    fun `default annotation produces valid sigml`() {
        val out = SignRenderer().render(surface())
        assertTrue(out.valid, "errors=${out.errors}")
        assertEquals(true, (out.payload["avatar_ok"] as kotlinx.serialization.json.JsonPrimitive).content.toBoolean())
    }

    @Test
    fun `xml format matches python exactly`() {
        val r = SignRenderer()
        val xml = r.convert("sym:hamfinger2", "test")
        val expected =
            "<sigml xmlns=\"https://vhg.cmp.uea.ac.uk/tech/jas/sigml\">\n" +
                "  <hns_sign gloss=\"test\">\n" +
                "    <hamnosys_manual>\n" +
                "      <hamfinger2 />\n" +
                "    </hamnosys_manual>\n" +
                "  </hns_sign>\n" +
                "</sigml>"
        assertEquals(expected, xml)
    }

    @Test
    fun `empty annotation produces self-closing manual`() {
        val r = SignRenderer()
        val xml = r.convert("", "test")
        val expected =
            "<sigml xmlns=\"https://vhg.cmp.uea.ac.uk/tech/jas/sigml\">\n" +
                "  <hns_sign gloss=\"test\">\n" +
                "    <hamnosys_manual />\n" +
                "  </hns_sign>\n" +
                "</sigml>"
        assertEquals(expected, xml)
    }

    @Test
    fun `unknown symbol appears as hamunknown`() {
        val r = SignRenderer()
        val xml = r.convert("sym:hamnotarealsymbol", "test")
        assertTrue("hamunknown" in xml)
        assertTrue("sym=\"hamnotarealsymbol\"" in xml)
    }

    @Test
    fun `validate rejects unknown symbol`() {
        val out = SignRenderer().render(surface(), hamnosys = "sym:hamnotarealsymbol")
        assertEquals(false, out.valid)
        assertTrue(out.errors.any { "unknown_symbol" in it })
    }

    @Test
    fun `attribute escaping`() {
        val r = SignRenderer()
        val xml = r.convert("sym:hamfinger2", "a<b&c\"d")
        assertTrue("gloss=\"a&lt;b&amp;c&quot;d\"" in xml)
    }
}
