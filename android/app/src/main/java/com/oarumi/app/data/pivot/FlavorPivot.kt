package com.oarumi.app.data.pivot

/**
 * Main-source-set wrapper around the flavor-specific PivotAvailability.
 * Referencing this from BootstrapManager keeps the flavor flag in one place.
 */
object FlavorPivot {
    val hasMlKit: Boolean get() = PivotAvailability.HAS_MLKIT
    val name: String get() = PivotAvailability.FLAVOR_NAME
}
