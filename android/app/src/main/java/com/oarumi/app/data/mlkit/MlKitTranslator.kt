package com.oarumi.app.data.mlkit

/**
 * Interface so the argos flavor can compile without the ML Kit dependency.
 * The mlkit flavor provides [RealMlKitTranslator]; the argos flavor provides
 * no binding (BootstrapManager receives null).
 */
interface MlKitTranslator {
    fun supportedLanguages(): Set<String>

    suspend fun isDownloaded(sourceLang: String): Boolean

    suspend fun ensureModel(sourceLang: String): Boolean

    suspend fun translate(
        text: String,
        sourceLang: String,
        offline: Boolean = false,
    ): String

    fun close()
}
