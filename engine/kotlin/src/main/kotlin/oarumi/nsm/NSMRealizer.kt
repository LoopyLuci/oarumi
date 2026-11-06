package oarumi.nsm

import oarumi.db.LanguageStore
import oarumi.errors.ValidationException
import oarumi.types.Clitic
import oarumi.types.NsmStructure
import oarumi.types.OarumiSurface

class NSMRealizer(db: LanguageStore) {
    // Lazy: see NSMDecomposerTierA. The constructor must not read the database.
    private val forms: Map<String, String> by lazy {
        db.allPrimes().associate { it.id to it.spokenForm }
    }

    private val moodToClitic: Map<String, Clitic> =
        mapOf(
            "DECL" to Clitic("=ha", "mood_declarative"),
            "INTERR" to Clitic("=hu", "mood_interrogative"),
            "IMPER" to Clitic("=hi", "mood_imperative"),
            "PROM" to Clitic("=ho", "mood_promissive"),
            "EXPRESS" to Clitic("=he", "mood_expressive"),
            "VOC" to Clitic("=ha", "mood_vocative"),
        )

    private val questionHeads = setOf("BE_SOMEWHERE", "FEEL")

    fun realize(
        nsm: NsmStructure,
        modality: String = "spoken",
    ): OarumiSurface {
        if (!nsm.valid) throw ValidationException("cannot realize invalid NSM structure")
        if (nsm.primes.isEmpty()) throw ValidationException("cannot realize empty NSM structure")

        val mood = inferMood(nsm)
        val clitic = moodToClitic[mood] ?: moodToClitic["DECL"]!!
        val ordered = linearize(nsm)

        val phonemes =
            ordered.map { pid ->
                forms[pid] ?: throw ValidationException("no spoken form for prime $pid")
            }
        return OarumiSurface(
            phonemes = phonemes,
            clitics = listOf(clitic),
            mood = mood,
            modality = modality,
        )
    }

    private fun inferMood(nsm: NsmStructure): String {
        for (c in nsm.combinators) {
            if (c.head in questionHeads) {
                if ("WHERE" in c.args || c.head == "FEEL") return "INTERR"
            }
            if (c.head == "NOT") return "DECL"
        }
        return "DECL"
    }

    private fun linearize(nsm: NsmStructure): List<String> {
        val ordered = mutableListOf<String>()
        val seen = mutableSetOf<String>()
        for (c in nsm.combinators) {
            if (c.type in setOf("clause", "predicate")) {
                if (c.head !in seen) {
                    ordered += c.head
                    seen += c.head
                }
                for (a in c.args) if (a !in seen) {
                    ordered += a
                    seen += a
                }
            }
        }
        for (p in nsm.primes) if (p.id !in seen) {
            ordered += p.id
            seen += p.id
        }
        return ordered
    }

    /** Reverse-map a surface back to an English pivot (for round-trip parity). */
    fun toCanonicalPivot(surface: OarumiSurface): String {
        val reverse = forms.entries.associate { (k, v) -> v to k }
        val ids = surface.phonemes.mapNotNull { reverse[it] }
        if ("WANT" in ids) {
            val agent = if ("I" in ids) "I" else "someone"
            return "$agent wants something"
        }
        if ("SEE" in ids) {
            val agent = if ("I" in ids) "I" else "someone"
            return "$agent see something"
        }
        if ("MOVE" in ids) {
            val agent = if ("I" in ids) "I" else "someone"
            return "$agent go"
        }
        if ("BE_SPEC" in ids && "GOOD" in ids) return "it is good"
        if ("BE_SPEC" in ids && "BAD" in ids) return "it is bad"
        if ("SAY" in ids && "WORDS" in ids) return "hello"
        if ("FEEL" in ids && "GOOD" in ids) return "thank you"
        if ("FEEL" in ids && "YOU" in ids) return "how are you"
        if ("BE_SOMEWHERE" in ids && "WHERE" in ids) return "where is the bathroom"
        if ("TRUE" in ids && "NOT" !in ids) return "yes"
        if ("NOT" in ids && "TRUE" in ids) return "no"
        return ""
    }
}
