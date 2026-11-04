package oarumi.reliability

import java.util.concurrent.atomic.AtomicInteger
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class WatchdogTest {
    @Test
    fun `completion prevents timeout`() {
        val fired = AtomicInteger(0)
        val wd = Watchdog(onTimeout = { fired.incrementAndGet() }, tickMs = 5)
        wd.start()
        try {
            val h = wd.arm("x", deadlineS = 0.5)
            wd.completed(h)
            Thread.sleep(200)
            assertEquals(0, fired.get())
        } finally {
            wd.stop()
        }
    }

    @Test
    fun `timeout fires when deadline passes`() {
        val fired = AtomicInteger(0)
        val wd = Watchdog(onTimeout = { fired.incrementAndGet() }, tickMs = 5)
        wd.start()
        try {
            val h = wd.arm("x", deadlineS = 0.05)
            val end = System.currentTimeMillis() + 500
            while (fired.get() == 0 && System.currentTimeMillis() < end) Thread.sleep(10)
            assertEquals(1, fired.get())
            assertTrue(h.isFired())
        } finally {
            wd.stop()
        }
    }

    @Test
    fun `callback exception does not kill the watchdog`() {
        val wd =
            Watchdog(
                onTimeout = { throw RuntimeException("handler failed") },
                tickMs = 5,
            )
        wd.start()
        try {
            wd.arm("a", deadlineS = 0.02)
            wd.arm("b", deadlineS = 0.02)
            Thread.sleep(150)
            // If the scheduler died, arm+timeout would not fire again.
            wd.arm("c", deadlineS = 0.02)
            Thread.sleep(150)
        } finally {
            wd.stop()
        }
    }
}
