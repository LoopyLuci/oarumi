package com.oarumi.app.data.update

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

object UpdateScheduler {
    const val UNIQUE_NAME = "oarumi-update-check"

    /** Turns the background check on or off. It runs at most every 12 hours, on a network. */
    fun setEnabled(
        context: Context,
        enabled: Boolean,
    ) {
        val work = WorkManager.getInstance(context)
        if (!enabled) {
            work.cancelUniqueWork(UNIQUE_NAME)
            return
        }
        val request =
            PeriodicWorkRequestBuilder<UpdateWorker>(12, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        work.enqueueUniquePeriodicWork(UNIQUE_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
    }
}
