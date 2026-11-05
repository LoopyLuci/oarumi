package oarumi.lang

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import java.security.MessageDigest

/** One row of the pack index. Mirrors engine/python/oarumi/lang/packs.py. */
data class PackEntry(
    val code: String,
    val name: String,
    val base: Boolean,
    val spell: Boolean,
    val detect: Boolean,
    val file: String,
    val sizeBytes: Long,
    val sha256: String,
)

data class LanguagePack(
    val code: String,
    val name: String,
    val base: Boolean,
    val words: Map<String, Int>,
    val ngrams: Map<String, Int>,
)

class PackException(message: String) : Exception(message)

private val packJson = Json { ignoreUnknownKeys = true }

fun parsePackIndex(text: String): List<PackEntry> {
    val packs = packJson.parseToJsonElement(text).jsonObject["packs"]?.jsonArray ?: return emptyList()
    return packs.map { element ->
        val item = element.jsonObject
        PackEntry(
            code = item.string("code"),
            name = item.string("name"),
            base = item.getValue("base").jsonPrimitive.booleanOrNull ?: false,
            spell = item.getValue("spell").jsonPrimitive.booleanOrNull ?: false,
            detect = item.getValue("detect").jsonPrimitive.booleanOrNull ?: false,
            file = item.string("file"),
            sizeBytes = item.getValue("size_bytes").jsonPrimitive.long,
            sha256 = item.string("sha256"),
        )
    }
}

/** Throws [PackException] unless [blob] matches the size and SHA-256 in [entry]. */
fun verifyPack(
    blob: ByteArray,
    entry: PackEntry,
) {
    if (blob.size.toLong() != entry.sizeBytes) {
        throw PackException("${entry.code}: size ${blob.size} does not match index ${entry.sizeBytes}")
    }
    val digest = MessageDigest.getInstance("SHA-256").digest(blob).joinToString("") { "%02x".format(it) }
    if (digest != entry.sha256) throw PackException("${entry.code}: checksum mismatch")
}

fun parsePack(text: String): LanguagePack {
    val data = packJson.parseToJsonElement(text).jsonObject
    return LanguagePack(
        code = data.string("code"),
        name = data.string("name"),
        base = data.getValue("base").jsonPrimitive.booleanOrNull ?: false,
        words = wordCounts(data.getValue("words").jsonArray),
        ngrams = data.getValue("ngrams").jsonObject.mapValues { it.value.jsonPrimitive.int },
    )
}

private fun wordCounts(pairs: JsonArray): Map<String, Int> {
    val counts = LinkedHashMap<String, Int>(pairs.size)
    for (pair in pairs) {
        val items = pair.jsonArray
        counts[items[0].jsonPrimitive.content] = items[1].jsonPrimitive.int
    }
    return counts
}

private fun JsonObject.string(key: String): String = getValue(key).jsonPrimitive.contentOrNull ?: ""
