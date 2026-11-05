package com.oarumi.app.data.update

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/** Per-device update settings. Nothing here is shared between users. */
@Singleton
class UpdatePreferences
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) {
        private val prefs = context.getSharedPreferences("oarumi_updates", Context.MODE_PRIVATE)

        var autoDownload: Boolean
            get() = prefs.getBoolean(KEY_AUTO_DOWNLOAD, false)
            set(value) {
                prefs.edit().putBoolean(KEY_AUTO_DOWNLOAD, value).apply()
            }

        var pendingVersion: String?
            get() = prefs.getString(KEY_PENDING_VERSION, null)
            set(value) {
                prefs.edit().putString(KEY_PENDING_VERSION, value).apply()
            }

        var pendingApkPath: String?
            get() = prefs.getString(KEY_PENDING_PATH, null)
            set(value) {
                prefs.edit().putString(KEY_PENDING_PATH, value).apply()
            }

        private companion object {
            const val KEY_AUTO_DOWNLOAD = "auto_download"
            const val KEY_PENDING_VERSION = "pending_version"
            const val KEY_PENDING_PATH = "pending_path"
        }
    }
