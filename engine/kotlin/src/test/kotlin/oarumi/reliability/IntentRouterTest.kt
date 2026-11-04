package oarumi.reliability

import oarumi.db.LanguageDb
import oarumi.types.TranslationRequest
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals

class IntentRouterTest {
    private val dbPath: Path =
        Path.of(System.getProperty("oarumi.db") ?: "../language/oarumi.db")

    private fun router(
        offline: Boolean = true,
        neural: Set<String> = emptySet(),
        modalities: Set<String> = setOf("spoken", "signed", "tactile", "text"),
    ): IntentRouter {
        val db = LanguageDb(dbPath)
        return IntentRouter(
            StaticCapabilitySource(
                db = db,
                offline = offline,
                neuralLangs = neural,
                modalities = modalities,
            ),
        )
    }

    @Test
    fun `empty input refuses`() {
        val r = router().route(TranslationRequest(text = "   ", lang = "es"))
        assertEquals("refuse", r.kind)
        assertEquals("empty_input", r.reason)
    }

    @Test
    fun `unsupported language refuses`() {
        val r = router().route(TranslationRequest(text = "hola", lang = "xx"))
        assertEquals("refuse", r.kind)
        assertEquals("unsupported_language", r.reason)
    }

    @Test
    fun `unsupported modality refuses`() {
        val r =
            router(modalities = setOf("text"))
                .route(TranslationRequest(text = "hola", lang = "es", modality = "spoken"))
        assertEquals("refuse", r.kind)
        assertEquals("unsupported_modality", r.reason)
    }

    @Test
    fun `phrasebook hit is direct`() {
        val r = router().route(TranslationRequest(text = "hola", lang = "es"))
        assertEquals("direct_deterministic", r.kind)
        assertEquals("phrasebook_hit", r.reason)
    }

    @Test
    fun `neural available for phrasebook miss`() {
        val r =
            router(offline = false, neural = setOf("es"))
                .route(TranslationRequest(text = "unknown phrase", lang = "es"))
        assertEquals("neural_candidate", r.kind)
        assertEquals("neural_pivot_available", r.reason)
    }

    @Test
    fun `no path refuses`() {
        val r =
            router()
                .route(TranslationRequest(text = "not in book", lang = "es"))
        assertEquals("refuse", r.kind)
        assertEquals("no_pivot_path", r.reason)
    }
}
