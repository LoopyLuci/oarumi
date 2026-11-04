package oarumi.renderers

import java.io.ByteArrayOutputStream
import java.nio.file.Files
import java.nio.file.Path
import kotlin.math.PI
import kotlin.math.sin

/**
 * Minimal WAV I/O matching Python's wave-module behavior for mono 16-bit PCM.
 * All click/hum assets are mono 16-bit, so this is sufficient.
 */
object WavWriter {
    data class WavData(val sampleRate: Int, val pcm: ByteArray)

    fun read(path: Path): WavData {
        val bytes = Files.readAllBytes(path)
        require(bytes.size >= 44) { "WAV too short: $path" }
        require(readAscii(bytes, 0, 4) == "RIFF") { "not RIFF: $path" }
        require(readAscii(bytes, 8, 4) == "WAVE") { "not WAVE: $path" }
        require(readAscii(bytes, 12, 4) == "fmt ") { "no fmt chunk: $path" }

        val sampleRate = readUInt32LE(bytes, 24)
        val dataOffset = findChunk(bytes, "data")
        require(dataOffset >= 0) { "no data chunk: $path" }
        val dataSize = readUInt32LE(bytes, dataOffset + 4)
        val start = dataOffset + 8
        val pcm = bytes.copyOfRange(start, start + dataSize)
        return WavData(sampleRate = sampleRate, pcm = pcm)
    }

    fun write(
        path: Path,
        sampleRate: Int,
        pcm: ByteArray,
    ) {
        val header = buildHeader(sampleRate, pcm.size)
        path.parent?.let { Files.createDirectories(it) }
        Files.write(path, header + pcm)
    }

    fun toneSamples(
        token: String,
        sampleRate: Int,
    ): ByteArray {
        val durationS = 0.09
        val n = (sampleRate * durationS).toInt()
        val byteSum = token.toByteArray(Charsets.UTF_8).sumOf { it.toInt() and 0xFF }
        val freq = 180.0 + (byteSum % 220)
        val out = ByteArrayOutputStream(n * 2)
        for (i in 0 until n) {
            val env = sin(PI * i / n)
            val sample = (12000 * env * sin(2 * PI * freq * i / sampleRate)).toInt()
            out.write(sample and 0xFF)
            out.write((sample shr 8) and 0xFF)
        }
        return out.toByteArray()
    }

    fun durationMs(path: Path): Int =
        try {
            val d = read(path)
            (1000L * (d.pcm.size / 2) / d.sampleRate).toInt()
        } catch (e: Exception) {
            0
        }

    // --- internals ------------------------------------------------------

    private fun readAscii(
        bytes: ByteArray,
        off: Int,
        len: Int,
    ): String = String(bytes, off, len, Charsets.US_ASCII)

    private fun readUInt32LE(
        bytes: ByteArray,
        off: Int,
    ): Int =
        (bytes[off].toInt() and 0xFF) or
            ((bytes[off + 1].toInt() and 0xFF) shl 8) or
            ((bytes[off + 2].toInt() and 0xFF) shl 16) or
            ((bytes[off + 3].toInt() and 0xFF) shl 24)

    private fun findChunk(
        bytes: ByteArray,
        id: String,
    ): Int {
        var i = 12
        while (i + 8 <= bytes.size) {
            val tag = readAscii(bytes, i, 4)
            val size = readUInt32LE(bytes, i + 4)
            if (tag == id) return i
            i += 8 + size + (size and 1) // chunks are word-aligned
        }
        return -1
    }

    private fun buildHeader(
        sampleRate: Int,
        pcmSize: Int,
    ): ByteArray {
        val byteRate = sampleRate * 2 // mono 16-bit
        val out = ByteArrayOutputStream(44)

        fun writeAscii(s: String) = out.write(s.toByteArray(Charsets.US_ASCII))

        fun writeUInt32(v: Int) {
            out.write(v and 0xFF)
            out.write((v shr 8) and 0xFF)
            out.write((v shr 16) and 0xFF)
            out.write((v shr 24) and 0xFF)
        }

        fun writeUInt16(v: Int) {
            out.write(v and 0xFF)
            out.write((v shr 8) and 0xFF)
        }
        writeAscii("RIFF")
        writeUInt32(36 + pcmSize)
        writeAscii("WAVE")
        writeAscii("fmt ")
        writeUInt32(16)
        writeUInt16(1) // PCM
        writeUInt16(1) // channels
        writeUInt32(sampleRate)
        writeUInt32(byteRate)
        writeUInt16(2) // block align
        writeUInt16(16) // bits per sample
        writeAscii("data")
        writeUInt32(pcmSize)
        return out.toByteArray()
    }
}
