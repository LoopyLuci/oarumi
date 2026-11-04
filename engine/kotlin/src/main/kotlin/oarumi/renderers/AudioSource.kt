package oarumi.renderers

import java.nio.file.Files
import java.nio.file.Path

/**
 * Platform-neutral access to the audio asset bundle.
 *
 * The JVM implementation reads from the file system; the Android
 * implementation (Batch 10) reads via AssetManager. The AudioAssetLibrary
 * itself only needs to read text and bytes.
 */
interface AudioSource {
    fun exists(relPath: String): Boolean

    fun readText(relPath: String): String

    fun readBytes(relPath: String): ByteArray
}

class FileSystemAudioSource(private val baseDir: Path) : AudioSource {
    override fun exists(relPath: String): Boolean = Files.exists(baseDir.resolve(relPath))

    override fun readText(relPath: String): String = Files.readString(baseDir.resolve(relPath))

    override fun readBytes(relPath: String): ByteArray = Files.readAllBytes(baseDir.resolve(relPath))
}
