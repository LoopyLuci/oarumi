package oarumi.reliability

import oarumi.types.ValidationOutcome
import kotlin.io.path.createTempDirectory
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull

class ShieldTest {
    private val valid = ValidationOutcome(true, emptyList())
    private val invalid = ValidationOutcome(false, listOf("bad"))

    private fun shield(): SymbolicShield {
        val dir = createTempDirectory("oarumi-shield-")
        return SymbolicShield(AuditLog(dir.resolve("audit.jsonl")))
    }

    @Test
    fun `use neural when valid`() {
        val call =
            shield().wrap<Int, String>(
                component = "x",
                neural = { "ok" },
                validator = { valid },
                fallback = { "fb" },
                contract = ParityContract(validityRequired = true, latencyCeilingMs = 1000),
            )
        val r = call(1)
        assertEquals("use_neural", r.decision)
        assertEquals("ok", r.output)
    }

    @Test
    fun `use fallback when invalid`() {
        val call =
            shield().wrap<Int, String>(
                component = "x",
                neural = { "bad" },
                validator = { invalid },
                fallback = { "fb" },
                contract = ParityContract(validityRequired = true, latencyCeilingMs = 1000),
            )
        val r = call(1)
        assertEquals("use_fallback", r.decision)
        assertEquals("fb", r.output)
        assertEquals("invalid", r.reason)
    }

    @Test
    fun `use fallback when neural raises`() {
        val call =
            shield().wrap<Int, String>(
                component = "x",
                neural = { throw RuntimeException("boom") },
                validator = { valid },
                fallback = { "fb" },
                contract = ParityContract(),
            )
        val r = call(1)
        assertEquals("use_fallback", r.decision)
        assertEquals("exception:RuntimeException", r.reason)
    }

    @Test
    fun `refuse when both fail`() {
        val call =
            shield().wrap<Int, String>(
                component = "x",
                neural = { "bad" },
                validator = { invalid },
                fallback = { throw RuntimeException("fb") },
                contract = ParityContract(),
            )
        val r = call(1)
        assertEquals("refuse", r.decision)
        assertNull(r.output)
        assertNotNull(r.reason)
    }

    @Test
    fun `decision is audited`() {
        val dir = createTempDirectory("oarumi-shield-")
        val path = dir.resolve("audit.jsonl")
        val log = AuditLog(path)
        val call =
            SymbolicShield(log).wrap<Int, String>(
                component = "pivot",
                neural = { "bad" },
                validator = { invalid },
                fallback = { "fb" },
                contract = ParityContract(),
            )
        call(1)
        val raw = path.toFile().readText()
        assertEquals(true, raw.contains("shield_decision"))
        assertEquals(true, raw.contains("use_fallback"))
    }
}
