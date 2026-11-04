package oarumi.reliability

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

data class WatchdogHandle(
    val component: String,
    val deadlineAtNanos: Long,
    val done: AtomicBoolean = AtomicBoolean(false),
    val fired: AtomicBoolean = AtomicBoolean(false),
) {
    fun isDone() = done.get()

    fun isFired() = fired.get()
}

/**
 * Deadline tracker on a single daemon scheduler thread.
 *
 * Uses ScheduledExecutorService so the same code runs on the JVM (tests) and
 * on Android (which also has java.util.concurrent since API 1).
 *
 * The watchdog never blocks the caller. `completed()` sets an AtomicBoolean;
 * the scheduler notices on the next tick.
 */
class Watchdog(
    private val onTimeout: (WatchdogHandle) -> Unit,
    private val tickMs: Long = 50L,
) {
    init {
        require(tickMs > 0) { "tickMs must be positive" }
    }

    private val scheduler: ScheduledExecutorService =
        Executors.newSingleThreadScheduledExecutor { r ->
            Thread(r, "oarumi-watchdog").apply { isDaemon = true }
        }

    private val handles = ConcurrentHashMap<Long, WatchdogHandle>()
    private val seq = AtomicLong(0)

    @Volatile private var started = false

    @Volatile private var stopped = false

    @Synchronized
    fun start() {
        if (started) return
        started = true
        scheduler.scheduleAtFixedRate({ runTick() }, 0, tickMs, TimeUnit.MILLISECONDS)
    }

    fun stop() {
        stopped = true
        scheduler.shutdownNow()
    }

    fun arm(
        component: String,
        deadlineS: Double,
    ): WatchdogHandle {
        require(deadlineS > 0) { "deadlineS must be positive" }
        val now = System.nanoTime()
        val h =
            WatchdogHandle(
                component = component,
                deadlineAtNanos = now + (deadlineS * 1_000_000_000L).toLong(),
            )
        handles[seq.incrementAndGet()] = h
        return h
    }

    fun completed(h: WatchdogHandle) {
        h.done.set(true)
    }

    private fun runTick() {
        if (stopped) return
        val now = System.nanoTime()
        val fired = mutableListOf<WatchdogHandle>()
        val it = handles.entries.iterator()
        while (it.hasNext()) {
            val entry = it.next()
            val h = entry.value
            if (h.done.get()) {
                it.remove()
                continue
            }
            if (now >= h.deadlineAtNanos && !h.fired.get()) {
                h.fired.set(true)
                fired += h
                it.remove()
            }
        }
        for (h in fired) {
            runCatching { onTimeout(h) } // callbacks must not kill the scheduler
        }
    }
}
