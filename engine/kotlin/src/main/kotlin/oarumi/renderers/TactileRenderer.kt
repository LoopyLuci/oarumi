package oarumi.renderers

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.OarumiSurface
import java.security.MessageDigest

/**
 * Bit-identical port of Python's TactileRenderer.
 *
 * The `_select` decision tree and `_referent_id` hashing are the two
 * deterministic pieces the parity test compares.
 */
class TactileRenderer(private val modality: String = "tactile") {
    companion object {
        val CONSTRUCTIONS: Map<String, Map<String, String>> =
            mapOf(
                "T001" to
                    mapOf(
                        "conveyer_hand" to "right",
                        "receiver_location" to "left_forearm",
                        "movement" to "linear",
                        "contact" to "light",
                        "gloss" to "referent_established",
                    ),
                "T002" to
                    mapOf(
                        "conveyer_hand" to "left",
                        "receiver_location" to "right_forearm",
                        "movement" to "circular",
                        "contact" to "firm",
                        "gloss" to "location_here",
                    ),
                "T003" to
                    mapOf(
                        "conveyer_hand" to "both",
                        "receiver_location" to "chest",
                        "movement" to "tap",
                        "contact" to "light",
                        "gloss" to "self_reference",
                    ),
                "T004" to
                    mapOf(
                        "conveyer_hand" to "right",
                        "receiver_location" to "left_palm",
                        "movement" to "hold",
                        "contact" to "firm",
                        "gloss" to "object_given",
                    ),
                "T005" to
                    mapOf(
                        "conveyer_hand" to "left",
                        "receiver_location" to "right_shoulder",
                        "movement" to "press",
                        "contact" to "firm",
                        "gloss" to "attention_request",
                    ),
            )
    }

    fun render(surface: OarumiSurface): RenderOutput {
        val cid = select(surface)
        val base = CONSTRUCTIONS[cid]!!
        val protocol =
            linkedMapOf<String, JsonPrimitive>(
                "construction_id" to JsonPrimitive(cid),
                "conveyer_hand" to JsonPrimitive(base["conveyer_hand"]),
                "receiver_location" to JsonPrimitive(base["receiver_location"]),
                "movement" to JsonPrimitive(base["movement"]),
                "contact" to JsonPrimitive(base["contact"]),
                "referent_id" to JsonPrimitive(referentId(surface)),
                "gloss" to JsonPrimitive(base["gloss"]),
            )
        val errors = validate(protocol.mapValues { (_, v) -> v.content })
        return RenderOutput(
            modality = modality,
            payload = mapOf("protocol" to JsonObject(protocol)),
            valid = errors.isEmpty(),
            errors = errors,
        )
    }

    private fun select(surface: OarumiSurface): String {
        val forms = surface.clitics.map { it.type }.toSet()
        val tokens = surface.phonemes.toSet()
        if (surface.mood == "INTERR") {
            return if ("lonu" in tokens || "where" in tokens) "T002" else "T005"
        }
        if (surface.mood == "IMPER") return "T004"
        if (surface.mood == "PROM") return "T003"
        if (surface.mood == "EXPRESS") return "T005"
        if (surface.mood == "VOC") return "T003"
        if ("mood_declarative" in forms) return "T001"
        return "T001"
    }

    private fun referentId(surface: OarumiSurface): String {
        val joined = surface.phonemes.joinToString("|")
        val digest =
            MessageDigest.getInstance("SHA-256")
                .digest(joined.toByteArray(Charsets.UTF_8))
        val hex = digest.joinToString("") { "%02x".format(it) }
        return "r${hex.take(8)}"
    }

    private fun validate(fields: Map<String, String>): List<String> {
        val errors = mutableListOf<String>()
        val required =
            setOf(
                "construction_id",
                "conveyer_hand",
                "receiver_location",
                "movement",
                "contact",
                "referent_id",
            )
        for (k in required) if (k !in fields) errors += "missing:$k"
        if (fields["conveyer_hand"] !in setOf("left", "right", "both")) {
            errors += "bad_conveyer_hand"
        }
        if (fields["contact"] !in setOf("light", "firm")) {
            errors += "bad_contact"
        }
        return errors
    }
}
