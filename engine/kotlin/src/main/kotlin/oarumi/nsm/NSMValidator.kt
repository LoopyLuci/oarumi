package oarumi.nsm

import oarumi.db.LanguageStore
import oarumi.types.NsmStructure
import oarumi.types.ValidationOutcome

class NSMValidator(db: LanguageStore) {
    // Lazy: see NSMDecomposerTierA. The constructor must not read the database.
    private val known: Set<String> by lazy { db.allPrimes().map { it.id }.toSet() }

    fun validate(nsm: NsmStructure): ValidationOutcome {
        val errors = mutableListOf<String>()
        if (nsm.primes.isEmpty()) errors += "no primes"
        if (nsm.combinators.isEmpty()) errors += "no combinators"

        val seen = mutableSetOf<String>()
        for (p in nsm.primes) {
            if (p.id !in known) errors += "unknown prime: ${p.id}"
            if (!seen.add(p.id)) errors += "duplicate prime: ${p.id}"
        }
        for (c in nsm.combinators) {
            if (c.type !in setOf("clause", "predicate", "modifier", "quote", "conditional")) {
                errors += "bad combinator type: ${c.type}"
            }
            if (c.head !in known) errors += "unknown head: ${c.head}"
            for (a in c.args) if (a !in known) errors += "unknown arg: $a"
        }
        return ValidationOutcome(errors.isEmpty(), errors)
    }
}
