package com.oarumi.app.data.update

import android.content.Context
import com.oarumi.app.data.net.HttpFetch
import com.oarumi.app.data.net.sha256Hex
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import oarumi.updates.Release
import oarumi.updates.ReleaseAsset
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

class UpdateException(
    message: String,
) : Exception(message)

/**
 * Downloads a release APK into the app cache. A file is kept only when its
 * SHA-256 matches the checksum published with the release.
 */
@Singleton
class UpdateDownloader
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
        private val prefs: UpdatePreferences,
    ) {
        /** Swappable for tests. */
        internal var fetch: (String) -> ByteArray = { url -> HttpFetch.bytes(url) }

        suspend fun download(
            release: Release,
            asset: ReleaseAsset,
        ): File =
            withContext(Dispatchers.IO) {
                val expected =
                    asset.sha256
                        ?: throw UpdateException(
                            "This release has no checksum, so the app will not install it. " +
                                "Download it from the release page.",
                        )
                val blob = fetch(asset.url)
                if (sha256Hex(blob) != expected) {
                    throw UpdateException("The download did not match the release checksum. It was discarded.")
                }
                val dir = File(context.cacheDir, UPDATE_DIR).apply { mkdirs() }
                dir.listFiles()?.forEach { it.delete() }
                val target = File(dir, asset.name)
                target.writeBytes(blob)
                prefs.pendingApkPath = target.absolutePath
                prefs.pendingVersion = release.tag
                target
            }

        companion object {
            const val UPDATE_DIR = "updates"
        }
    }
