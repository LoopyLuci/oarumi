package com.oarumi.app.data.pivot

/**
 * Flavor-specific marker: ML Kit is available in the mlkit flavor.
 * The BootstrapManager checks this flag to decide whether per-language
 * downloads are needed.
 */
object PivotAvailability {
    const val HAS_MLKIT: Boolean = true
    const val FLAVOR_NAME: String = "mlkit"
}
