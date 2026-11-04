package oarumi.reliability

import oarumi.db.LanguageStore
import oarumi.pivot.Phrasebook
import oarumi.types.Route
import oarumi.types.TranslationRequest

interface CapabilitySource {
    fun hasLanguage(lang: String): Boolean

    fun hasModality(modality: String): Boolean

    fun isOffline(): Boolean

    fun hasNeuralPivot(
        src: String,
        dst: String,
    ): Boolean

    fun hasPhrasebook(src: String): Boolean
}

data class StaticCapabilitySource(
    @Suppress("UNUSED_PARAMETER") val db: LanguageStore? = null,
    val offline: Boolean = false,
    val extraLangs: Set<String> = emptySet(),
    val neuralLangs: Set<String> = emptySet(),
    val modalities: Set<String> = setOf("spoken", "signed", "tactile", "text"),
) : CapabilitySource {
    private val phrasebookLangs: Set<String> = Phrasebook.supportedLanguages().toSet()

    override fun hasLanguage(lang: String) = lang in extraLangs || lang in phrasebookLangs

    override fun hasModality(modality: String) = modality in modalities

    override fun isOffline() = offline

    override fun hasNeuralPivot(
        src: String,
        dst: String,
    ) = !offline && src in neuralLangs && dst == "en"

    override fun hasPhrasebook(src: String) = src in phrasebookLangs
}

class IntentRouter(val source: CapabilitySource) {
    fun route(req: TranslationRequest): Route {
        val text = req.text.trim()
        if (text.isEmpty()) return Route("refuse", "empty_input")

        if (!source.hasLanguage(req.lang)) {
            return Route("refuse", "unsupported_language", listOf(req.lang))
        }

        if (!source.hasModality(req.modality)) {
            return Route("refuse", "unsupported_modality", listOf(req.modality))
        }

        // Phrasebook hit: deterministic, zero-latency.
        if (source.hasPhrasebook(req.lang) && Phrasebook.lookup(req.lang, text) != null) {
            return Route("direct_deterministic", "phrasebook_hit", listOf("phrasebook"))
        }

        // Otherwise, a neural path is viable if the adapter is installed.
        if (source.hasNeuralPivot(req.lang, "en")) {
            return Route("neural_candidate", "neural_pivot_available", listOf("pivot_adapter"))
        }

        return Route("refuse", "no_pivot_path", listOf(req.lang))
    }
}
