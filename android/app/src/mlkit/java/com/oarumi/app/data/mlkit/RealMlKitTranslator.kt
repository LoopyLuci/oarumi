package com.oarumi.app.data.mlkit

import android.content.Context
import com.google.android.gms.tasks.Task
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import oarumi.errors.CapabilityMissingException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class RealMlKitTranslator(
    @Suppress("UNUSED_PARAMETER") private val context: Context,
) :
    MlKitTranslator {
    private val mutex = Mutex()
    private val translators = mutableMapOf<String, Translator>()

    override fun supportedLanguages(): Set<String> = TranslateLanguage.getAllLanguages().toSet()

    override suspend fun isDownloaded(sourceLang: String): Boolean {
        if (sourceLang == TranslateLanguage.ENGLISH) return true
        val t = obtain(sourceLang) ?: return false
        return suspendCancellableCoroutine { cont ->
            t.downloadModelIfNeeded(DownloadConditions.Builder().build())
                .addOnSuccessListener { cont.resume(true) }
                .addOnFailureListener { cont.resume(false) }
        }
    }

    override suspend fun ensureModel(sourceLang: String): Boolean =
        mutex.withLock {
            if (sourceLang == TranslateLanguage.ENGLISH) return true
            val t =
                translators.getOrPut("$sourceLang>en") {
                    val opts =
                        TranslatorOptions.Builder()
                            .setSourceLanguage(sourceLang)
                            .setTargetLanguage(TranslateLanguage.ENGLISH)
                            .build()
                    Translation.getClient(opts)
                }
            try {
                await(t.downloadModelIfNeeded(DownloadConditions.Builder().build()))
                true
            } catch (e: Exception) {
                false
            }
        }

    override suspend fun translate(
        text: String,
        sourceLang: String,
        offline: Boolean,
    ): String {
        if (text.isBlank()) return ""
        if (sourceLang == TranslateLanguage.ENGLISH) return text
        if (sourceLang !in supportedLanguages()) {
            throw CapabilityMissingException(
                "ML Kit does not support '$sourceLang'",
                capability = "mlkit:$sourceLang",
            )
        }
        @Suppress("UNUSED_EXPRESSION")
        offline
        val t = obtain(sourceLang)!!
        return await(t.translate(text))
    }

    override fun close() {
        translators.values.forEach { it.close() }
        translators.clear()
    }

    private fun obtain(sourceLang: String): Translator? {
        if (sourceLang == TranslateLanguage.ENGLISH) return null
        return translators.getOrPut("$sourceLang>en") {
            val opts =
                TranslatorOptions.Builder()
                    .setSourceLanguage(sourceLang)
                    .setTargetLanguage(TranslateLanguage.ENGLISH)
                    .build()
            Translation.getClient(opts)
        }
    }

    private suspend fun <T> await(task: Task<T>): T =
        suspendCancellableCoroutine { cont ->
            task.addOnSuccessListener { v -> cont.resume(v) }
                .addOnFailureListener { e -> cont.resumeWithException(e) }
        }
}
