package com.oarumi.app.bootstrap

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.work.ListenableWorker
import androidx.work.WorkerFactory
import androidx.work.WorkerParameters
import androidx.work.testing.TestListenableWorkerBuilder
import com.oarumi.app.data.mlkit.MlKitTranslator
import com.oarumi.app.data.tts.AndroidTtsBackend
import kotlinx.coroutines.runBlocking
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.test.Test
import kotlin.test.assertEquals

@RunWith(RobolectricTestRunner::class)
class BootstrapWorkerTest {
    private class FakeMlKit(private val succeed: Boolean) : MlKitTranslator {
        override fun supportedLanguages() = setOf("es", "en")

        override suspend fun isDownloaded(sourceLang: String) = succeed

        override suspend fun ensureModel(sourceLang: String) = succeed

        override suspend fun translate(
            text: String,
            sourceLang: String,
            offline: Boolean,
        ) = text

        override fun close() = Unit
    }

    @Test
    fun `worker succeeds when downloads succeed`() {
        val ctx = ApplicationProvider.getApplicationContext<Context>()
        val store = BootstrapStateStore()
        val tts = AndroidTtsBackend(ctx)
        try {
            val manager = BootstrapManager(ctx, store, tts, FakeMlKit(true))
            val worker =
                TestListenableWorkerBuilder<BootstrapWorker>(ctx)
                    .setWorkerFactory(
                        object : WorkerFactory() {
                            override fun createWorker(
                                appContext: Context,
                                workerClassName: String,
                                workerParameters: WorkerParameters,
                            ): ListenableWorker = BootstrapWorker(appContext, workerParameters, manager)
                        },
                    )
                    .build()
            val result = runBlocking { worker.doWork() }
            assertEquals(ListenableWorker.Result.success(), result)
        } finally {
            tts.close()
        }
    }
}
