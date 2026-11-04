package oarumi.reliability

/**
 * Convenience aggregator so callers only need one import.
 *
 * Batch 8 does not wire this into Pipeline yet; Batch 10 (Android data layer)
 * and Batch 14 (parity web) will consume it.
 */
data class ReliabilityStack(
    val audit: AuditLog,
    val watchdog: Watchdog,
    val shield: SymbolicShield,
    val router: IntentRouter,
    val canary: Canary,
) {
    companion object {
        fun create(
            auditPath: java.nio.file.Path,
            canaryRoot: java.nio.file.Path,
            capabilities: CapabilitySource,
            onTimeout: ((WatchdogHandle) -> Unit)? = null,
        ): ReliabilityStack {
            val audit = AuditLog(auditPath)
            val wd =
                Watchdog(
                    onTimeout =
                        onTimeout ?: { h ->
                            audit.logSimple(
                                "watchdog", "timeout",
                                "component" to h.component,
                            )
                        },
                )
            wd.start()
            val shield = SymbolicShield(audit = audit, watchdog = wd)
            val router = IntentRouter(capabilities)
            val canary = Canary(canaryRoot)
            return ReliabilityStack(audit, wd, shield, router, canary)
        }
    }
}
