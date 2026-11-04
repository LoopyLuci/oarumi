package oarumi.reliability

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import oarumi.types.ValidationOutcome
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.createTempDirectory
import kotlin.io.path.readText
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * Loads tests/parity/data/reliability/scenarios.json (also consumed by the
 * Python shield test) and asserts that the Kotlin shield makes the same
 * decision the Python shield is expected to make.
 */
class CrossLanguageShieldTest {
    private val fixtureDir: Path =
        Path.of(System.getProperty("oarumi.parity.data") ?: "../tests/parity/data")
            .resolve("reliability")

    @Test
    fun `kotlin shield matches python scenarios`() {
        val file = fixtureDir.resolve("scenarios.json")
        if (!Files.exists(file)) return // tolerate fresh clone before Batch 13

        val scenarios =
            Json.parseToJsonElement(file.readText()).jsonObject["scenarios"]!!
                .jsonArray

        for (s in scenarios) {
            val obj = s.jsonObject
            val name = obj["name"]!!.jsonPrimitive.content
            val neuralSpec = obj["neural"]!!.jsonObject
            val fallbackSpec = obj["fallback"]!!.jsonObject
            val contractSpec = obj["contract"]!!.jsonObject
            val expectedDecision = obj["expected_decision"]!!.jsonPrimitive.content

            val neuralReturns = neuralSpec["returns"]?.jsonPrimitive?.content
            val neuralRaises = neuralSpec["raises"]?.jsonPrimitive?.content
            val fallbackReturns = fallbackSpec["returns"]?.jsonPrimitive?.content
            val fallbackRaises = fallbackSpec["raises"]?.jsonPrimitive?.content

            val validityRequired =
                contractSpec["validity_required"]!!.jsonPrimitive.content.toBoolean()
            val latencyCeiling =
                contractSpec["latency_ceiling_ms"]!!.jsonPrimitive.content.toLong()

            val auditPath = createTempDirectory("xl-$name-").resolve("audit.jsonl")
            val shield = SymbolicShield(AuditLog(auditPath))

            val call =
                shield.wrap<Int, String>(
                    component = name,
                    neural = {
                        if (neuralRaises != null) throw RuntimeException("simulated")
                        "x"
                    },
                    validator = {
                        if (neuralReturns == "valid") {
                            ValidationOutcome(true)
                        } else {
                            ValidationOutcome(false, listOf("bad"))
                        }
                    },
                    fallback = {
                        if (fallbackRaises != null) throw RuntimeException("simulated")
                        "fb"
                    },
                    contract =
                        ParityContract(
                            validityRequired = validityRequired,
                            latencyCeilingMs = latencyCeiling,
                        ),
                )
            val r = call(1)
            assertEquals(
                expectedDecision,
                r.decision,
                "scenario '$name' produced '${r.decision}' (reason='${r.reason}')",
            )
        }
    }
}
