package com.oarumi.app.ui.translate

import oarumi.types.TranslationResult

data class TranslateUiState(
    val availableLanguages: List<String> = listOf("es", "fr", "de", "zh", "ar"),
    val sourceLanguage: String = "es",
    val targetModality: String = "spoken",
    val inputText: String = "",
    val isTranslating: Boolean = false,
    val result: TranslationResult? = null,
    val statusMessage: String = "Ready.",
    val error: String? = null,
) {
    val showDegraded: Boolean get() = result?.degraded == true

    val formattedOutput: String
        get() {
            val r = result ?: return ""
            val sb = StringBuilder()
            sb.appendLine("Surface:   ${r.surface.surfaceString()}")
            sb.appendLine("Mood:      ${r.surface.mood}")
            sb.appendLine("Pivot:     ${r.pivot.text} (${r.pivot.source})")
            sb.appendLine("Degraded:  ${r.degraded}")

            r.modalities.forEach { (modality, payload) ->
                sb.appendLine()
                sb.appendLine("[$modality]")
                when (modality) {
                    "spoken" -> {
                        sb.appendLine("  audio_path: ${payload["audio_path"] ?: "—"}")
                        sb.appendLine("  backend:    ${payload["backend"] ?: "—"}")
                        sb.appendLine(
                            "  phonemes:   ${(payload["phoneme_stream"] as? List<*>)?.joinToString(" ") ?: ""}",
                        )
                    }
                    "signed" -> {
                        sb.appendLine("  sigml:")
                        val sigml =
                            (payload["sigml"] as? kotlinx.serialization.json.JsonPrimitive)?.content
                                ?: payload["sigml"]?.toString() ?: ""
                        sigml.split("\n").forEach { line -> sb.appendLine("    $line") }
                    }
                    "tactile" -> {
                        sb.appendLine("  protocol:")
                        val proto = payload["protocol"]?.toString() ?: "{}"
                        proto.split(",").forEach { part -> sb.appendLine("    $part") }
                    }
                    else -> sb.appendLine("  $payload")
                }
            }

            if (r.failoverEvents.isNotEmpty()) {
                sb.appendLine()
                sb.appendLine("Failover events:")
                r.failoverEvents.forEach { ev ->
                    sb.appendLine("  ${ev.component}: ${ev.trigger} @ ${ev.t}")
                }
            }
            return sb.toString()
        }

    val traceLines: List<String>
        get() {
            val r = result ?: return emptyList()
            val lines = mutableListOf<String>()
            r.trace.forEach { lines += "${it.step} (${it.path}): ${it.reason}" }
            r.failoverEvents.forEach { lines += "failover: ${it.component} / ${it.trigger}" }
            return lines
        }
}
