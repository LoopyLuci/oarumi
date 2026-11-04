package oarumi

import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject

/**
 * Strip the fields that cannot be equal across platforms or across runs.
 * Mirrors tools/parity_runner.py::_canonical.
 */
object JsonCanonicalizer {
    fun canonical(element: JsonElement?): JsonElement? {
        if (element == null) return null
        val obj = element.jsonObject
        val out = obj.toMutableMap()

        out.remove("request_id")

        val events = out["failover_events"]?.jsonArray
        if (events != null) {
            val cleaned =
                events.map { ev ->
                    val evObj = ev.jsonObject.toMutableMap()
                    evObj.remove("t")
                    JsonObject(evObj)
                }
            out["failover_events"] = kotlinx.serialization.json.JsonArray(cleaned)
        }

        val mods = out["modalities"]?.jsonObject
        if (mods != null) {
            val cleaned =
                mods.mapValues { (_, v) ->
                    val vObj = v.jsonObject.toMutableMap()
                    vObj.remove("audio_path")
                    vObj.remove("duration_ms")
                    JsonObject(vObj)
                }
            out["modalities"] = JsonObject(cleaned)
        }

        return JsonObject(out)
    }

    fun isEphemeral(key: String): Boolean =
        key in
            setOf(
                "request_id", "audio_path", "duration_ms",
            )

    @Suppress("unused")
    private fun unusedPrimitive(p: JsonPrimitive) = p // keep import
}
