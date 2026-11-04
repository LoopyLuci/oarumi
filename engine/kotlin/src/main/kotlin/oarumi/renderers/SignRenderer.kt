package oarumi.renderers

import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.OarumiSurface
import org.w3c.dom.Element
import javax.xml.parsers.DocumentBuilderFactory

/**
 * Bit-identical port of Python's HamNoSysToSigML._builtin + validate_sigml.
 *
 * Emits:
 *   <sigml xmlns="https://vhg.cmp.uea.ac.uk/tech/jas/sigml">
 *     <hns_sign gloss="...">
 *       <hamnosys_manual>
 *         <symbol />
 *         ...
 *       </hamnosys_manual>
 *     </hns_sign>
 *   </sigml>
 *
 * Formatting matches Python's ElementTree.tostring(...) + ET.indent(2 spaces).
 */
class SignRenderer(
    private val useExternal: Boolean = false,
    private val modality: String = "signed",
) {
    companion object {
        const val SIGML_NS = "https://vhg.cmp.uea.ac.uk/tech/jas/sigml"
        private const val SIGML_ROOT = "sigml"
        private const val HNS_SIGN = "hns_sign"
        private const val MANUAL = "hamnosys_manual"

        val ALLOWED_SYMBOLS: Set<String> =
            setOf(
                "hamfinger2", "hamthumbout", "hamnohandchange", "hamarcsym",
                "hamextfingeru", "hamextfingerd", "hamextfingerl", "hamextfingerr",
                "hampalmd", "hampalmr", "hampalmup", "hampalmdown",
                "hamshoulders", "hamchest", "hamwaist", "hamhead",
                "hammoveo", "hammoveu", "hammoved", "hammovel", "hammover",
                "hamrepeat", "hamplus", "hamsmallmod", "hamlargemod",
                "hamtouch", "hamcircle", "hamstraight",
            )

        private val TOKEN_RE = Regex("""^(?:sym:)?(?<name>ham[a-z0-9_]+)$""")
    }

    fun render(
        surface: OarumiSurface,
        hamnosys: String? = null,
        gloss: String? = null,
    ): RenderOutput {
        val annotation =
            hamnosys
                ?: "sym:hamfinger2 sym:hamthumbout sym:hamnohandchange sym:hamarcsym sym:hamextfingeru"
        val useGloss =
            gloss
                ?: surface.phonemes.firstOrNull()
                ?: "UNKNOWN"

        val xml = convert(annotation, useGloss)
        val (ok, errors) = validateSigml(xml)
        return RenderOutput(
            modality = modality,
            payload =
                mapOf(
                    "sigml" to JsonPrimitive(xml),
                    "avatar_ok" to JsonPrimitive(ok),
                    "gloss" to JsonPrimitive(useGloss),
                ),
            valid = ok,
            errors = errors,
        )
    }

    fun convert(
        annotation: String,
        gloss: String,
    ): String {
        val sb = StringBuilder()
        sb.append("<").append(SIGML_ROOT).append(" xmlns=\"").append(SIGML_NS).append("\">\n")
        sb.append("  <").append(HNS_SIGN).append(" gloss=\"").append(escapeAttr(gloss)).append("\">\n")

        val symbols = mutableListOf<Pair<String, String?>>() // (tag, sym-attr)
        for (raw in annotation.split(Regex("\\s+"))) {
            if (raw.isEmpty()) continue
            val m = TOKEN_RE.matchEntire(raw)
            if (m == null) {
                symbols += "hamunknown" to raw
                continue
            }
            val name = m.groups["name"]!!.value
            if (name !in ALLOWED_SYMBOLS) {
                symbols += "hamunknown" to name
            } else {
                symbols += name to null
            }
        }

        if (symbols.isEmpty()) {
            sb.append("    <").append(MANUAL).append(" />\n")
        } else {
            sb.append("    <").append(MANUAL).append(">\n")
            for ((tag, sym) in symbols) {
                sb.append("      <").append(tag)
                if (sym != null) {
                    sb.append(" sym=\"").append(escapeAttr(sym)).append("\"")
                }
                sb.append(" />\n")
            }
            sb.append("    </").append(MANUAL).append(">\n")
        }

        sb.append("  </").append(HNS_SIGN).append(">\n")
        sb.append("</").append(SIGML_ROOT).append(">")
        return sb.toString()
    }

    private fun escapeAttr(s: String): String =
        buildString {
            for (c in s) {
                when (c) {
                    '&' -> append("&amp;")
                    '<' -> append("&lt;")
                    '>' -> append("&gt;")
                    '"' -> append("&quot;")
                    else -> append(c)
                }
            }
        }

    private fun validateSigml(xml: String): Pair<Boolean, List<String>> {
        val errors = mutableListOf<String>()
        val doc =
            try {
                DocumentBuilderFactory.newInstance()
                    .newDocumentBuilder()
                    .parse(xml.byteInputStream())
            } catch (e: Exception) {
                return false to listOf("parse_error:${e.message}")
            }
        val root = doc.documentElement
        if (root.tagName != SIGML_ROOT) errors += "root:${root.tagName}"
        val signs = root.getElementsByTagName(HNS_SIGN)
        if (signs.length != 1) {
            errors += "hns_sign_count:${signs.length}"
            return (errors.isEmpty()) to errors
        }
        val sign = signs.item(0) as Element
        if (!sign.hasAttribute("gloss")) errors += "hns_sign:missing_gloss"
        val manuals = sign.getElementsByTagName(MANUAL)
        if (manuals.length != 1) {
            errors += "hamnosys_manual:missing"
            return (errors.isEmpty()) to errors
        }
        val manual = manuals.item(0) as Element
        val children = manual.childNodes
        for (i in 0 until children.length) {
            val node = children.item(i) as? Element ?: continue
            val name = node.tagName
            if (name == "hamunknown") {
                errors += "unknown_symbol:${node.getAttribute("sym")}"
            } else if (name !in ALLOWED_SYMBOLS) {
                errors += "unexpected_element:$name"
            }
        }
        return (errors.isEmpty()) to errors
    }
}
