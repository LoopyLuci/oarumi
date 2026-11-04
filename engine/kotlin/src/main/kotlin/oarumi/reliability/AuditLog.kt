package oarumi.reliability

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.UUID

/**
 * Byte-identical to the Python AuditLog:
 *   - one JSON object per line
 *   - no whitespace
 *   - key order: id, t, component, event, payload
 *   - rotation at maxBytes (10 MB default)
 */
@Serializable
data class AuditEvent(
    val id: String,
    val t: String,
    val component: String,
    val event: String,
    val payload: JsonObject = JsonObject(emptyMap()),
) {
    companion object {
        private val isoFormatter =
            DateTimeFormatter
                .ofPattern("yyyy-MM-dd'T'HH:mm:ss")
                .withZone(ZoneOffset.UTC)

        fun make(
            component: String,
            event: String,
            payload: Map<String, JsonElement>,
        ): AuditEvent =
            AuditEvent(
                id = UUID.randomUUID().toString(),
                t = isoFormatter.format(Instant.now()),
                component = component,
                event = event,
                payload = JsonObject(payload),
            )

        /** Variant that accepts primitives so callers do not build JsonElements by hand. */
        fun make(
            component: String,
            event: String,
            vararg pairs: Pair<String, Any?>,
        ): AuditEvent {
            val map =
                buildJsonObject {
                    for ((k, v) in pairs) {
                        when (v) {
                            null -> put(k, JsonPrimitive(""))
                            is String -> put(k, JsonPrimitive(v))
                            is Boolean -> put(k, JsonPrimitive(v))
                            is Int -> put(k, JsonPrimitive(v))
                            is Long -> put(k, JsonPrimitive(v))
                            is Double -> put(k, JsonPrimitive(v))
                            is Float -> put(k, JsonPrimitive(v))
                            else -> put(k, JsonPrimitive(v.toString()))
                        }
                    }
                }
            return AuditEvent(
                id = UUID.randomUUID().toString(),
                t = isoFormatter.format(Instant.now()),
                component = component,
                event = event,
                payload = map,
            )
        }
    }
}

private val AUDIT_JSON =
    Json {
        encodeDefaults = true
        explicitNulls = false
        prettyPrint = false
    }

class AuditLog(
    val path: Path,
    private val maxBytes: Long = 10L * 1024 * 1024,
) {
    private val lock = Any()

    init {
        path.parent?.let { Files.createDirectories(it) }
    }

    fun log(event: AuditEvent) {
        val line = AUDIT_JSON.encodeToString(AuditEvent.serializer(), event)
        synchronized(lock) {
            rotateIfNeeded((line.toByteArray(Charsets.UTF_8).size + 1).toLong())
            Files.write(
                path,
                (line + "\n").toByteArray(Charsets.UTF_8),
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND,
            )
        }
    }

    fun logSimple(
        component: String,
        event: String,
        vararg pairs: Pair<String, Any?>,
    ) {
        log(AuditEvent.make(component, event, *pairs))
    }

    fun replay(): List<AuditEvent> {
        val out = mutableListOf<AuditEvent>()
        val dir = path.parent ?: return out
        if (!Files.exists(dir)) return out
        val rotated =
            Files.list(dir)
                .filter { it.fileName.toString().startsWith("${path.fileName}.") }
                .sorted()
                .toList()
        for (f in rotated) out += readFile(f)
        out += readFile(path)
        return out
    }

    private fun readFile(p: Path): List<AuditEvent> {
        if (!Files.exists(p)) return emptyList()
        return Files.readAllLines(p, Charsets.UTF_8)
            .filter { it.isNotBlank() }
            .mapNotNull { line ->
                runCatching {
                    AUDIT_JSON.decodeFromString(AuditEvent.serializer(), line)
                }.getOrNull()
            }
    }

    private fun rotateIfNeeded(incoming: Long) {
        if (!Files.exists(path)) return
        val size = runCatching { Files.size(path) }.getOrDefault(0L)
        if (size + incoming <= maxBytes) return
        val stamp =
            DateTimeFormatter
                .ofPattern("yyyyMMdd'T'HHmmss")
                .withZone(ZoneOffset.UTC)
                .format(Instant.now())
        // Two rotations in the same second must not collide (matches the Python AuditLog).
        var target = path.resolveSibling("${path.fileName}.$stamp")
        var n = 1
        while (Files.exists(target)) {
            target = path.resolveSibling("${path.fileName}.$stamp.$n")
            n += 1
        }
        Files.move(path, target)
    }
}
