package com.oarumi.app.data.apk

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import com.oarumi.app.BuildConfig
import com.oarumi.app.data.update.ApkInstaller
import com.oarumi.app.data.update.installedVersion
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/** Saves or shares the APK this app was installed from. */
@Singleton
class ApkExport
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        fun suggestedName(): String = "oarumi-${BuildConfig.FLAVOR}-${installedVersion(BuildConfig.VERSION_NAME)}.apk"

        /** Copies the installed APK to a location the user picked in the system file picker. */
        suspend fun saveTo(destination: Uri) {
            withContext(Dispatchers.IO) {
                val output =
                    context.contentResolver.openOutputStream(destination)
                        ?: throw IOException("Cannot write to the chosen file.")
                output.use { out -> installedApk().inputStream().use { it.copyTo(out) } }
            }
        }

        /** Copies the APK into the share cache and returns a send intent for the chooser. */
        suspend fun shareIntent(): Intent =
            withContext(Dispatchers.IO) {
                val dir = File(context.cacheDir, SHARE_DIR).apply { mkdirs() }
                dir.listFiles()?.forEach { it.delete() }
                val copy = File(dir, suggestedName())
                installedApk().copyTo(copy, overwrite = true)
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", copy)
                Intent(Intent.ACTION_SEND)
                    .setType(ApkInstaller.APK_MIME)
                    .putExtra(Intent.EXTRA_STREAM, uri)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }

        private fun installedApk(): File = File(context.applicationInfo.sourceDir)

        private companion object {
            const val SHARE_DIR = "share"
        }
    }
