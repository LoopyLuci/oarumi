package oarumi.reliability

import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.ValidationOutcome

data class ParityContract(
    val validityRequired: Boolean = true,
    val latencyCeilingMs: Long = 2000L,
    val requireDoubleRunEqual: Boolean = false,
)

data class ShieldResult<O>(
    // "use_neural" | "use_fallback" | "refuse"
    val decision: String,
    val output: O?,
    val reason: String,
    val latencyMs: Double,
)

class SymbolicShield(
    private val audit: AuditLog,
    private val watchdog: Watchdog? = null,
) {
    fun <I, O> wrap(
        component: String,
        neural: (I) -> O,
        validator: (O) -> ValidationOutcome,
        fallback: (I) -> O,
        contract: ParityContract,
        normalizer: ((O) -> String)? = null,
    ): (I) -> ShieldResult<O> {
        return fn@{ input ->
            val t0 = System.nanoTime()

            var neuralOutput: O? = null
            var neuralReason = "ok"

            try {
                neuralOutput =
                    if (watchdog != null) {
                        val handle = watchdog.arm(component, contract.latencyCeilingMs / 1000.0)
                        try {
                            neural(input)
                        } finally {
                            watchdog.completed(handle)
                        }
                    } else {
                        neural(input)
                    }
            } catch (e: Exception) {
                neuralReason = "exception:${e::class.simpleName ?: "Unknown"}"
            }

            val latencyMs = (System.nanoTime() - t0) / 1_000_000.0

            if (neuralOutput != null && neuralReason == "ok") {
                val outcome = validator(neuralOutput)
                if (contract.validityRequired && !outcome.valid) {
                    neuralReason = "invalid"
                } else if (latencyMs > contract.latencyCeilingMs) {
                    neuralReason = "latency"
                } else if (contract.requireDoubleRunEqual && normalizer != null) {
                    val second = neural(input)
                    if (normalizer(neuralOutput) != normalizer(second)) {
                        neuralReason = "inconsistent"
                    }
                }
            }

            if (neuralOutput != null && neuralReason == "ok") {
                audit.logSimple(
                    component,
                    "shield_decision",
                    "decision" to "use_neural",
                    "latency_ms" to latencyMs,
                )
                return@fn ShieldResult(
                    decision = "use_neural",
                    output = neuralOutput,
                    reason = "ok",
                    latencyMs = latencyMs,
                )
            }

            // Fallback.
            val fb: O? =
                try {
                    fallback(input)
                } catch (e: Exception) {
                    audit.logSimple(
                        component,
                        "shield_decision",
                        "decision" to "refuse",
                        "neural_reason" to neuralReason,
                        "fallback_error" to (e::class.simpleName ?: "Unknown"),
                    )
                    return@fn ShieldResult(
                        decision = "refuse",
                        output = null,
                        reason = "fallback_failed:${e::class.simpleName ?: "Unknown"}",
                        latencyMs = latencyMs,
                    )
                }

            audit.logSimple(
                component,
                "shield_decision",
                "decision" to "use_fallback",
                "neural_reason" to neuralReason,
                "latency_ms" to latencyMs,
            )
            ShieldResult(
                decision = "use_fallback",
                output = fb,
                reason = neuralReason,
                latencyMs = latencyMs,
            )
        }
    }

    @Suppress("unused")
    private fun jp(s: String) = JsonPrimitive(s) // keep import usable
}
