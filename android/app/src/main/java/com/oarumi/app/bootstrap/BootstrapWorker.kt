package com.oarumi.app.bootstrap

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.oarumi.app.data.pivot.FlavorPivot
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

/**
 * Background worker that mirrors BootstrapManager.startBootstrap().
 *
 * Used when the wizard's per-language downloads should survive activity
 * rotation or the user navigating away. The wizard's own foreground flow
 * is the default; this worker is offered as "Continue in background".
 */
@HiltWorker
class BootstrapWorker
    @AssistedInject
    constructor(
        @Assisted context: Context,
        @Assisted params: WorkerParameters,
        private val manager: BootstrapManager,
    ) : CoroutineWorker(context, params) {
        override suspend fun doWork(): Result {
            if (!FlavorPivot.hasMlKit) {
                manager.startBootstrap()
                return Result.success()
            }
            return if (manager.startBootstrap()) Result.success() else Result.retry()
        }

        companion object {
            const val UNIQUE_NAME = "oarumi-bootstrap"
        }
    }
