package com.oarumi.app.data.pivot

/**
 * Flavor-specific marker: no ML Kit in the argos (phrasebook-only) flavor.
 * Everything is bundled; no downloads are required.
 */
object PivotAvailability {
    const val HAS_MLKIT: Boolean = false
    const val FLAVOR_NAME: String = "argos"
}
