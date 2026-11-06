package com.oarumi.app.data.update

import oarumi.updates.Release
import oarumi.updates.ReleaseAsset
import oarumi.updates.isNewer
import oarumi.updates.parseRelease
import oarumi.updates.pickApk

sealed interface UpdateStatus {
    data class UpToDate(
        val latest: String,
    ) : UpdateStatus

    /** [apk] is null when the release has no APK for this flavor. */
    data class Available(
        val release: Release,
        val apk: ReleaseAsset?,
    ) : UpdateStatus

    /** GitHub answers 404 for "latest release" until the first release is published. */
    data object NoRelease : UpdateStatus
}

/** The version this build reports, without the debug and flavor suffixes added by Gradle. */
fun installedVersion(versionName: String): String = versionName.removeSuffix("-debug").removeSuffix("-phrasebook")

/** Decides from the GitHub "latest release" JSON whether this build is behind. */
fun decideUpdate(
    releaseJson: String,
    installedVersion: String,
    flavor: String,
): UpdateStatus {
    val release = parseRelease(releaseJson)
    if (!isNewer(release.tag, installedVersion)) return UpdateStatus.UpToDate(release.tag)
    return UpdateStatus.Available(release, pickApk(release, flavor))
}
