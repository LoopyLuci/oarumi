package oarumi.reliability

import kotlinx.serialization.json.Json
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.createTempDirectory
import kotlin.io.path.writeText
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class CanaryTest {
    private val json = Json

    private fun writeCase(
        dir: Path,
        name: String,
        input: String,
        expected: String,
    ) {
        Files.createDirectories(dir)
        dir.resolve("$name.json").writeText("""{"input": $input, "expected": $expected}""")
    }

    @Test
    fun `no cases fails`() {
        val canary = Canary(createTempDirectory("canary-"))
        val r = canary.run("pivot") { it }
        assertFalse(r.passed)
        assertTrue("no_cases" in r.failures)
    }

    @Test
    fun `all pass`() {
        val dir = createTempDirectory("canary-")
        writeCase(dir.resolve("pivot"), "a", """{"x": 1}""", """{"y": 2}""")
        writeCase(dir.resolve("pivot"), "b", """{"x": 3}""", """{"y": 6}""")
        val canary = Canary(dir)
        val r =
            canary.run("pivot") { input ->
                // Double x's value.
                val x = input.toString().substringAfter(":").substringBefore("}").trim().toInt()
                json.parseToJsonElement("""{"y": ${x * 2}}""")
            }
        assertTrue(r.passed)
        assertEquals(2, r.total)
    }

    @Test
    fun `callback raises fails`() {
        val dir = createTempDirectory("canary-")
        writeCase(dir.resolve("pivot"), "a", """{"x": 1}""", """{"y": 2}""")
        val canary = Canary(dir)
        val r = canary.run("pivot") { throw RuntimeException("boom") }
        assertFalse(r.passed)
        assertTrue(r.failures.any { it.contains("raised:RuntimeException") })
    }
}
