package oarumi.nsm

import oarumi.db.LanguageStore
import oarumi.errors.ValidationException
import oarumi.types.NsmStructure

class NSMDecomposerTierA(private val db: LanguageStore) {
    // Lazy: reading the database here would run in the constructor, which
    // Android builds on the main thread at launch.
    private val known: Set<String> by lazy { db.allPrimes().map { it.id }.toSet() }

    fun decompose(pivot: String): NsmStructure {
        val text = pivot.trim()
        if (text.isEmpty()) throw ValidationException("empty pivot", listOf("empty pivot"))

        for (t in TEMPLATES) {
            val m = t.pattern.matchEntire(text) ?: continue
            val nsm = t.build(m)
            checkKnown(nsm)
            return nsm
        }
        throw ValidationException(
            "no template matched pivot '${text.take(60)}'",
            listOf("no-template:${text.take(40)}"),
        )
    }

    private fun checkKnown(nsm: NsmStructure) {
        val unknown = mutableListOf<String>()
        nsm.primes.forEach { if (it.id !in known) unknown += it.id }
        nsm.combinators.forEach { c ->
            if (c.head !in known) unknown += c.head
            c.args.forEach { if (it !in known) unknown += it }
        }
        if (unknown.isNotEmpty()) {
            val uniq = unknown.toSortedSet()
            throw ValidationException(
                "unknown prime id(s): $uniq",
                uniq.map { "unknown-prime:$it" },
            )
        }
    }
}
