package com.oarumi.app.data.net

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** Plain HTTPS GET used for language packs and release metadata. */
object HttpFetch {
    private const val TIMEOUT_MS = 20_000

    fun bytes(
        url: String,
        accept: String? = null,
    ): ByteArray {
        val connection =
            (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = TIMEOUT_MS
                readTimeout = TIMEOUT_MS
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", "oarumi-android")
                accept?.let { setRequestProperty("Accept", it) }
            }
        try {
            val code = connection.responseCode
            if (code !in 200..299) throw IOException("HTTP $code from $url")
            return connection.inputStream.use { it.readBytes() }
        } finally {
            connection.disconnect()
        }
    }
}

fun sha256Hex(bytes: ByteArray): String =
    MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
        "%02x".format(it)
    }
