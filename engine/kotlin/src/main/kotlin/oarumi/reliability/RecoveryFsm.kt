package oarumi.reliability

enum class FsmState { HEALTHY, DEGRADED, FAILED, RECOVERING }

data class Transition(
    val from: FsmState,
    val to: FsmState,
    val reason: String,
    // System.nanoTime()
    val t: Long,
)

class RecoveryFsm(
    val component: String,
    var onTransition: ((Transition) -> Unit)? = null,
) {
    var state: FsmState = FsmState.HEALTHY
        private set
    var attempt: Int = 0
        private set
    var lastRetryAt: Long = 0L
        private set
    val history: MutableList<Transition> = mutableListOf()

    private fun move(
        to: FsmState,
        reason: String,
    ) {
        if (to == FsmState.HEALTHY && state == FsmState.RECOVERING && reason != "canary_pass") {
            throw IllegalStateException(
                "cannot enter HEALTHY from RECOVERING without reason='canary_pass'",
            )
        }
        val tr = Transition(from = state, to = to, reason = reason, t = System.nanoTime())
        state = to
        history += tr
        onTransition?.invoke(tr)
    }

    fun onTrigger(reason: String = "trigger") {
        when (state) {
            FsmState.HEALTHY -> move(FsmState.DEGRADED, reason)
            FsmState.DEGRADED -> move(FsmState.FAILED, reason)
            else -> { /* no-op; Python is likewise silent */ }
        }
    }

    fun onCanaryPass() {
        if (state !in setOf(FsmState.DEGRADED, FsmState.FAILED, FsmState.RECOVERING)) return
        attempt = 0
        move(FsmState.RECOVERING, "canary_start")
        move(FsmState.HEALTHY, "canary_pass")
    }

    fun onCanaryFail() {
        if (state != FsmState.RECOVERING) {
            state = FsmState.FAILED // Python forces this then records the transition
        }
        attempt += 1
        lastRetryAt = System.nanoTime()
        move(FsmState.FAILED, "canary_fail")
    }

    fun onRollback() {
        attempt = 0
        move(FsmState.FAILED, "rollback")
    }

    fun backoffS(
        base: Double = 1.0,
        cap: Double = 60.0,
    ): Double = minOf(cap, base * Math.pow(2.0, maxOf(0, attempt - 1).toDouble()))

    fun readyForRetry(): Boolean {
        if (state != FsmState.FAILED) return false
        val elapsedS = (System.nanoTime() - lastRetryAt) / 1_000_000_000.0
        return elapsedS >= backoffS()
    }
}
