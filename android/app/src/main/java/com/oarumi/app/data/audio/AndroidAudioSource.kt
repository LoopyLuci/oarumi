package com.oarumi.app.data.audio

import android.content.res.AssetManager
import oarumi.renderers.AudioSource

/**
 * AudioSource implementation backed by the APK's assets/ folder.
 * The path convention (assets/audio/...) matches the JVM FileSystemAudioSource
 * rooted at the repo's assets/audio directory.
 */
class AndroidAudioSource(private val assets: AssetManager) : AudioSource {
    override fun exists(relPath: String): Boolean =
        try {
            assets.open("audio/$relPath").use { true }
        } catch (e: Exception) {
            false
        }

    override fun readText(relPath: String): String =
        assets.open("audio/$relPath").bufferedReader(Charsets.UTF_8).use { it.readText() }

    override fun readBytes(relPath: String): ByteArray = assets.open("audio/$relPath").use { it.readBytes() }
}
