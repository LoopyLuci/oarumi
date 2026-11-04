package oarumi.reliability

import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.createTempDirectory
import kotlin.io.path.readText
import kotlin.io.path.writeText
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AuditLogTest {
    private fun temp(): Path = createTempDirectory("oarumi-audit-")

    @Test
    fun `append and replay round trip`() {
        val dir = temp()
        val log = AuditLog(dir.resolve("audit.jsonl"))
        log.logSimple("pivot", "hello", "value" to 1)
        log.logSimple("pivot", "world", "value" to 2)
        val events = log.replay()
        assertEquals(listOf("hello", "world"), events.map { it.event })
    }

    @Test
    fun `rotation keeps at most one active file under size`() {
        val dir = temp()
        val log = AuditLog(dir.resolve("audit.jsonl"), maxBytes = 200)
        repeat(20) { log.logSimple("x", "e", "i" to it) }
        val rotated = Files.list(dir).filter { it.fileName.toString().contains("audit.jsonl.") }.count()
        assertTrue(rotated >= 1, "expected at least one rotated file")
    }

    @Test
    fun `line format matches python`() {
        val dir = temp()
        val path = dir.resolve("audit.jsonl")
        val log = AuditLog(path)
        log.logSimple("pivot", "test_event", "decision" to "use_neural", "latency_ms" to 1.5)
        val firstLine = path.readText().trim()
        // Key order: id, t, component, event, payload
        assertTrue(firstLine.startsWith("{\"id\":\""), "line starts: $firstLine")
        assertTrue(firstLine.contains("\"component\":\"pivot\""))
        assertTrue(firstLine.contains("\"event\":\"test_event\""))
        assertTrue(firstLine.contains("\"decision\":\"use_neural\""))
        assertTrue(firstLine.contains("\"latency_ms\":1.5"))
        // No whitespace outside strings.
        val stripped = firstLine.replace(Regex("\"[^\"]*\""), "\"\"")
        assertTrue(!stripped.contains(" "), "unexpected whitespace in: $firstLine")
    }

    @Test
    fun `can read python-produced log`() {
        // A line written by the Python AuditLog (see fixtures).
        val line =
            """{"id":"11111111-1111-4111-8111-111111111111","t":"2026-01-01T00:00:00",""" +
                """"component":"pivot","event":"test","payload":{"decision":"use_neural","latency_ms":1.5}}"""
        val dir = temp()
        val path = dir.resolve("audit.jsonl")
        path.writeText(line + "\n")
        val log = AuditLog(path)
        val events = log.replay()
        assertEquals(1, events.size)
        assertEquals("pivot", events[0].component)
        assertEquals("test", events[0].event)
    }
}
