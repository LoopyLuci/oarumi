package oarumi.reliability

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.jsonObject
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.extension
import kotlin.io.path.nameWithoutExtension
import kotlin.io.path.readText

data class CanaryCase(
    val name: String,
    val input: JsonElement,
    val expected: JsonElement,
)

data class CanaryResult(
    val passed: Boolean,
    val total: Int,
    val failures: List<String>,
)

class Canary(private val root: Path) {
    private val json = Json { ignoreUnknownKeys = true }

    fun load(component: String): List<CanaryCase> {
        val base = root.resolve(component)
        if (!Files.exists(base)) return emptyList()
        return Files.list(base)
            .filter { it.extension == "json" }
            .sorted()
            .map { path ->
                val obj = json.parseToJsonElement(path.readText()).jsonObject
                CanaryCase(
                    name = path.nameWithoutExtension,
                    input = obj["input"] ?: Json.parseToJsonElement("{}"),
                    expected = obj["expected"] ?: Json.parseToJsonElement("{}"),
                )
            }
            .toList()
    }

    fun run(
        component: String,
        call: (JsonElement) -> JsonElement,
    ): CanaryResult {
        val cases = load(component)
        if (cases.isEmpty()) {
            return CanaryResult(passed = false, total = 0, failures = listOf("no_cases"))
        }
        val failures = mutableListOf<String>()
        for (case in cases) {
            val got =
                try {
                    call(case.input)
                } catch (e: Exception) {
                    failures += "${case.name}:raised:${e::class.simpleName ?: "Unknown"}"
                    continue
                }
            if (got != case.expected) {
                failures += "${case.name}:mismatch"
            }
        }
        return CanaryResult(
            passed = failures.isEmpty(),
            total = cases.size,
            failures = failures,
        )
    }
}
