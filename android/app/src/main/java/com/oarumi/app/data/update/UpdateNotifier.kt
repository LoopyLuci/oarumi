package com.oarumi.app.data.update

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class UpdateNotifier
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        @Suppress("MissingPermission")
        fun updateReady(
            version: String,
            apk: File,
        ) {
            ensureChannel()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                return
            }
            val pending =
                PendingIntent.getActivity(
                    context,
                    REQUEST_CODE,
                    ApkInstaller.installIntent(context, apk),
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
                )
            val notification =
                NotificationCompat.Builder(context, CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.stat_sys_download_done)
                    .setContentTitle("Oarumi $version is ready")
                    .setContentText("Tap to install. Android will ask you to confirm.")
                    .setContentIntent(pending)
                    .setAutoCancel(true)
                    .build()
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification)
        }

        private fun ensureChannel() {
            val manager = context.getSystemService(NotificationManager::class.java)
            if (manager.getNotificationChannel(CHANNEL_ID) == null) {
                manager.createNotificationChannel(
                    NotificationChannel(CHANNEL_ID, "App updates", NotificationManager.IMPORTANCE_DEFAULT),
                )
            }
        }

        private companion object {
            const val CHANNEL_ID = "oarumi-updates"
            const val NOTIFICATION_ID = 4101
            const val REQUEST_CODE = 4102
        }
    }
