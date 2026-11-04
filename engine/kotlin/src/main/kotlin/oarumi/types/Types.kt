package oarumi.types

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** The single canonical serialization config used everywhere. */
val OarumiJson: Json =
    Json {
        encodeDefaults = true
        explicitNulls = false
        prettyPrint = false
        isLenient = true
    }

@Serializable
data class PrimeRef(val id: String, val role: String)

@Serializable
data class Combinator(
    val type: String,
    val head: String,
    val args: List<String>,
)

@Serializable
data class NsmStructure(
    val primes: List<PrimeRef>,
    val combinators: List<Combinator>,
    val valid: Boolean = true,
) {
    companion object {
        val EMPTY = NsmStructure(emptyList(), emptyList(), false)
    }
}

@Serializable
data class Clitic(val form: String, val type: String)

@Serializable
data class OarumiSurface(
    val phonemes: List<String>,
    val clitics: List<Clitic>,
    val mood: String,
    val modality: String,
) {
    fun surfaceString(): String = phonemes.joinToString(" ")

    companion object {
        fun empty(modality: String) =
            OarumiSurface(
                phonemes = emptyList(),
                clitics = emptyList(),
                mood = "DECL",
                modality = modality,
            )
    }
}

@Serializable
data class TranslationRequest(
    val text: String,
    val lang: String,
    val modality: String = "spoken",
    @SerialName("target_modality") val targetModality: String? = null,
) {
    fun toPayload(): InputPayload =
        InputPayload(text = text, lang = lang, modality = modality, targetModality = targetModality)
}

@Serializable
data class InputPayload(
    val text: String,
    val lang: String,
    val modality: String,
    @SerialName("target_modality") val targetModality: String? = null,
)

@Serializable
data class PivotPayload(val text: String, val lang: String, val source: String)

@Serializable
data class TraceEntry(val step: String, val path: String, val reason: String)

@Serializable
data class FailoverEvent(val component: String, val trigger: String, val t: String)

@Serializable
data class PivotResult(
    val text: String,
    val lang: String,
    val source: String,
    val trace: List<TraceEntry> = emptyList(),
)

@Serializable
data class TranslationResult(
    @SerialName("request_id") val requestId: String,
    val input: InputPayload,
    val pivot: PivotPayload,
    val nsm: NsmStructure,
    val surface: OarumiSurface,
    val modalities: Map<String, kotlinx.serialization.json.JsonObject> = emptyMap(),
    val trace: List<TraceEntry> = emptyList(),
    @SerialName("failover_events") val failoverEvents: List<FailoverEvent> = emptyList(),
    val degraded: Boolean = false,
)

/** Internal data class used by the router. */
data class Route(
    // "direct_deterministic" | "neural_candidate" | "refuse"
    val kind: String,
    val reason: String,
    val capabilities: List<String> = emptyList(),
)

@Serializable
data class ValidationOutcome(val valid: Boolean, val errors: List<String> = emptyList())
