package com.oarumi.app

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.oarumi.app.data.update.UpdatePreferences
import com.oarumi.app.data.update.UpdateScheduler
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class OarumiApp : Application(), Configuration.Provider {
    @Inject lateinit var workerFactory: HiltWorkerFactory

    @Inject lateinit var updatePreferences: UpdatePreferences

    override fun onCreate() {
        super.onCreate()
        // Keep the background update check running across app restarts when the user turned it on.
        if (updatePreferences.autoDownload) UpdateScheduler.setEnabled(this, enabled = true)
    }

    override val workManagerConfiguration: Configuration
        get() =
            Configuration.Builder()
                .setWorkerFactory(workerFactory)
                .build()
}
