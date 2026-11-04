package oarumi.renderers

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import oarumi.errors.IntegrityException
import java.security.MessageDigest

data class AudioAsset(
    val id: String,
    val relPath: String,
    val sha256: String,
    val sampleRate: Int,
)

/**
 * Parses assets/audio/manifest.json and verifies each file's hash.
 * Matches Python's AudioAssetLibrary semantics exactly.
 */
class AudioAssetLibrary(
    private val source: AudioSource,
    requireVerified: Boolean = false,
) {
    private val json = Json { ignoreUnknownKeys = true }

    private val assets: Map<String, AudioAsset>
    val sampleRate: Int

    init {
        if (!source.exists("manifest.json")) {
            throw java.io.FileNotFoundException("audio manifest missing: manifest.json")
        }
        val root = json.parseToJsonElement(source.readText("manifest.json")).jsonObject
        sampleRate = (root["sample_rate"]?.jsonPrimitive?.content?.toIntOrNull()) ?: 22050

        val map = mutableMapOf<String, AudioAsset>()
        for (entryElem in root["assets"]?.jsonArray ?: kotlinx.serialization.json.JsonArray(emptyList())) {
            val entry = entryElem.jsonObject
            val id = entry["id"]!!.jsonPrimitive.content
            val relPath = entry["path"]!!.jsonPrimitive.content
            val hash = entry["sha256"]?.jsonPrimitive?.content ?: ""
            val rate = entry["sample_rate"]?.jsonPrimitive?.content?.toIntOrNull() ?: sampleRate

            if (requireVerified && hash.isEmpty()) {
                throw IntegrityException(
                    "asset $id has no sha256; run tools/generate_audio_assets.py",
                )
            }
            if (!source.exists(relPath)) {
                throw java.io.FileNotFoundException("audio asset missing: $relPath")
            }
            if (hash.isNotEmpty()) {
                val actual = sha256Hex(source.readBytes(relPath))
                if (actual != hash) {
                    throw IntegrityException(
                        "asset $id hash mismatch: $actual != $hash",
                    )
                }
            }
            map[id] = AudioAsset(id = id, relPath = relPath, sha256 = hash, sampleRate = rate)
        }
        assets = map
    }

    fun get(id: String): AudioAsset = assets[id] ?: throw kotlin.NoSuchElementException("no audio asset '$id'")

    fun has(id: String): Boolean = id in assets

    fun ids(): List<String> = assets.keys.sorted()

    fun readBytes(asset: AudioAsset): ByteArray = source.readBytes(asset.relPath)

    private fun sha256Hex(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }

    @Suppress("unused")
    private fun unusedJsonObject(o: JsonObject) = o
}
