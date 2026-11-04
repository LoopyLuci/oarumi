package oarumi.pivot

import oarumi.config.EngineConfig
import oarumi.errors.FallbackRequiredException
import oarumi.types.PivotResult
import oarumi.types.TraceEntry

class PivotTranslator(private val config: EngineConfig) {
    fun translate(
        text: String,
        src: String,
        dst: String = "en",
    ): PivotResult {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) {
            return PivotResult(text = "", lang = dst, source = "passthrough")
        }
        if (src == dst) {
            return PivotResult(
                text = trimmed,
                lang = dst,
                source = "passthrough",
                trace = listOf(TraceEntry("pivot", "deterministic", "src==dst")),
            )
        }

        val hit = Phrasebook.lookup(src, trimmed)
        if (hit != null) {
            return PivotResult(
                text = hit,
                lang = dst,
                source = "phrasebook",
                trace = listOf(TraceEntry("pivot", "deterministic", "phrasebook-hit")),
            )
        }

        // Batch 7 does not ship an offline neural adapter yet (Batch 10 does).
        // When offline, refuse deterministically. When online, this would try
        // ML Kit (Android) — parity tests run with OARUMI_OFFLINE=1 so this
        // branch is exercised only in non-parity Android contexts.
        if (config.offline) {
            throw FallbackRequiredException(
                "no pivot path for lang=$src, text=${trimmed.take(40)}",
                component = "pivot",
                trigger = "unavailable",
            )
        }

        throw FallbackRequiredException(
            "no pivot path for lang=$src, text=${trimmed.take(40)}",
            component = "pivot",
            trigger = "unavailable",
        )
    }
}
