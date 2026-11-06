package oarumi.updates

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long

/**
 * Semantic version with pre-release identifiers. Mirrors engine/python/oarumi/updates.py:
 * a release sorts after its pre-releases, numeric identifiers sort before alphanumeric ones.
 */
data class Version(
    val core: Triple<Int, Int, Int>,
    val pre: List<Any>,
) : Comparable<Version> {
    override fun compareTo(other: Version): Int {
        if (core != other.core) return compareValuesBy(core, other.core, { it.first }, { it.second }, { it.third })
        if (pre == other.pre) return 0
        if (pre.isEmpty()) return 1
        if (other.pre.isEmpty()) return -1
        return compareIdentifiers(pre, other.pre)
    }

    private fun compareIdentifiers(
        left: List<Any>,
        right: List<Any>,
    ): Int {
        for (index in 0 until minOf(left.size, right.size)) {
            val a = left[index]
            val b = right[index]
            val result =
                when {
                    a is Int && b is Int -> a.compareTo(b)
                    a is Int -> -1
                    b is Int -> 1
                    else -> (a as String).compareTo(b as String)
                }
            if (result != 0) return result
        }
        return left.size.compareTo(right.size)
    }
}

fun parseVersion(text: String): Version {
    var body = text.trim()
    if (body.startsWith("v") || body.startsWith("V")) body = body.substring(1)
    body = body.substringBefore('+')
    val corePart = body.substringBefore('-')
    val prePart = if (body.contains('-')) body.substringAfter('-') else ""
    val parts = corePart.split('.')
    require(parts.size == 3 && parts.all { part -> part.isNotEmpty() && part.all { it.isDigit() } }) {
        "not a version: $text"
    }
    val pre: List<Any> =
        if (prePart.isEmpty()) {
            emptyList()
        } else {
            prePart.split('.').map { part -> if (part.all { it.isDigit() }) part.toInt() else part }
        }
    return Version(Triple(parts[0].toInt(), parts[1].toInt(), parts[2].toInt()), pre)
}

fun isNewer(
    latest: String,
    current: String,
): Boolean = parseVersion(current) < parseVersion(latest)

data class ReleaseAsset(
    val name: String,
    val url: String,
    val sizeBytes: Long,
    val sha256: String?,
)

data class Release(
    val tag: String,
    val htmlUrl: String,
    val assets: List<ReleaseAsset>,
) {
    val version: Version get() = parseVersion(tag)
}

fun parseRelease(json: String): Release {
    val data = Json.parseToJsonElement(json).jsonObject
    val assets =
        data["assets"]?.jsonArray?.map { element ->
            val item: JsonObject = element.jsonObject
            val digest = item["digest"]?.jsonPrimitive?.content
            ReleaseAsset(
                name = item.getValue("name").jsonPrimitive.content,
                url = item.getValue("browser_download_url").jsonPrimitive.content,
                sizeBytes = item["size"]?.jsonPrimitive?.long ?: 0L,
                sha256 = digest?.takeIf { it.startsWith("sha256:") }?.removePrefix("sha256:"),
            )
        } ?: emptyList()
    return Release(
        tag = data.getValue("tag_name").jsonPrimitive.content,
        htmlUrl = data.getValue("html_url").jsonPrimitive.content,
        assets = assets,
    )
}

/** The APK for one flavor. Names follow android/app/build.gradle.kts. */
fun pickApk(
    release: Release,
    flavor: String,
    buildType: String = "release",
): ReleaseAsset? {
    val prefix = "oarumi-$flavor-$buildType-"
    return release.assets.firstOrNull { it.name.startsWith(prefix) && it.name.endsWith(".apk") }
}
