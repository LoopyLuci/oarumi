package oarumi.renderers

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Envelope that mirrors the Python RenderOutput.to_json() shape:
 *
 *   {
 *     "modality": "...",
 *     ...payload...,
 *     "valid": true,
 *     "errors": [...]   // only when non-empty
 *   }
 */
data class RenderOutput(
    val modality: String,
    val payload: Map<String, JsonElement> = emptyMap(),
    val valid: Boolean = true,
    val errors: List<String> = emptyList(),
) {
    fun toJsonObject(): JsonObject {
        val map = LinkedHashMap<String, JsonElement>()
        map["modality"] = JsonPrimitive(modality)
        for ((k, v) in payload) map[k] = v
        map["valid"] = JsonPrimitive(valid)
        if (errors.isNotEmpty()) {
            map["errors"] = JsonArray(errors.map { JsonPrimitive(it) })
        }
        return JsonObject(map)
    }
}
