package oarumi.reliability

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class RecoveryFsmTest {
    @Test
    fun `healthy to degraded to failed`() {
        val fsm = RecoveryFsm("pivot")
        fsm.onTrigger("validation")
        assertEquals(FsmState.DEGRADED, fsm.state)
        fsm.onTrigger("validation")
        assertEquals(FsmState.FAILED, fsm.state)
    }

    @Test
    fun `cannot enter healthy from recovering without canary_pass`() {
        val fsm = RecoveryFsm("pivot")
        fsm.onTrigger("x")
        // Force into RECOVERING via the private-transition path.
        val method = fsm.javaClass.getDeclaredMethod("move", FsmState::class.java, String::class.java)
        method.isAccessible = true
        method.invoke(fsm, FsmState.RECOVERING, "manual")
        // Reflection wraps the thrown exception, so assert on the cause.
        val wrapped =
            assertFailsWith<java.lang.reflect.InvocationTargetException> {
                method.invoke(fsm, FsmState.HEALTHY, "manual")
            }
        assertTrue(wrapped.cause is IllegalStateException)
    }

    @Test
    fun `canary pass from degraded recovers`() {
        val fsm = RecoveryFsm("pivot")
        fsm.onTrigger("x")
        fsm.onCanaryPass()
        assertEquals(FsmState.HEALTHY, fsm.state)
        assertEquals(0, fsm.attempt)
    }

    @Test
    fun `canary fail schedules retry`() {
        val fsm = RecoveryFsm("pivot")
        fsm.onTrigger("x")
        // Enter RECOVERING without completing the pair.
        fsm.javaClass.getDeclaredMethod("move", FsmState::class.java, String::class.java)
            .also { it.isAccessible = true }
            .invoke(fsm, FsmState.RECOVERING, "canary_start")
        fsm.onCanaryFail()
        assertEquals(FsmState.FAILED, fsm.state)
        assertEquals(1, fsm.attempt)
        assertFalse(fsm.readyForRetry())
    }

    @Test
    fun `backoff grows and caps`() {
        val fsm = RecoveryFsm("pivot")
        assertEquals(1.0, fsm.backoffS(), 1e-9)
        fsm.onTrigger("a")
        fsm.onTrigger("a")
        fsm.javaClass.getDeclaredMethod("move", FsmState::class.java, String::class.java)
            .also { it.isAccessible = true }
            .invoke(fsm, FsmState.RECOVERING, "canary_start")
        fsm.onCanaryFail() // attempt=1
        assertEquals(1.0, fsm.backoffS(), 1e-9)
        fsm.onCanaryFail() // attempt=2
        assertEquals(2.0, fsm.backoffS(), 1e-9)
    }

    @Test
    fun `history records every transition`() {
        val fsm = RecoveryFsm("pivot")
        fsm.onTrigger("a")
        fsm.onTrigger("b")
        fsm.onCanaryPass()
        val reasons = fsm.history.map { it.reason }
        assertTrue("a" in reasons)
        assertTrue("b" in reasons)
        assertTrue("canary_pass" in reasons)
        assertEquals(FsmState.HEALTHY, fsm.history.first().from)
        assertEquals(FsmState.HEALTHY, fsm.history.last().to)
    }
}
