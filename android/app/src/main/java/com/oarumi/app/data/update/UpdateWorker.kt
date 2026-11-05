package com.oarumi.app.data.update

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.oarumi.app.BuildConfig
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.io.File
import java.io.IOException

/**
 * Periodic background check. When background downloads are on, it fetches a
 * new APK that matches the release checksum, then posts a notification. The
 * install itself still needs the user to confirm.
 */
@HiltWorker
class UpdateWorker
    @AssistedInject
    constructor(
        @Assisted context: Context,
        @Assisted params: WorkerParameters,
        private val checker: UpdateChecker,
        private val downloader: UpdateDownloader,
        private val prefs: UpdatePreferences,
        private val notifier: UpdateNotifier,
    ) : CoroutineWorker(context, params) {
        override suspend fun doWork(): Result {
            if (!prefs.autoDownload) return Result.success()
            return try {
                val status = checker.check(installedVersion(BuildConfig.VERSION_NAME), BuildConfig.FLAVOR)
                if (status !is UpdateStatus.Available) return Result.success()
                val apk = status.apk ?: return Result.success()
                val alreadyHave =
                    prefs.pendingVersion == status.release.tag &&
                        File(prefs.pendingApkPath ?: "").exists()
                if (!alreadyHave) {
                    val file = downloader.download(status.release, apk)
                    notifier.updateReady(status.release.tag, file)
                }
                Result.success()
            } catch (e: IOException) {
                Result.retry()
            } catch (e: UpdateException) {
                Result.success()
            }
        }
    }
