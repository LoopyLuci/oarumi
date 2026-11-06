package oarumi.lang

/** A word the dictionary does not know, with its span in the checked text. */
data class Misspelling(
    val start: Int,
    val end: Int,
    val word: String,
    val suggestions: List<String>,
)

/**
 * Dictionary spell checker with edit-distance suggestions. Mirrors
 * engine/python/oarumi/lang/spell.py: distance 1 first, distance 2 only when
 * distance 1 finds nothing, ranked by frequency and then by spelling.
 */
class SpellChecker(words: Map<String, Int>) {
    private val freq: Map<String, Int> = words.mapKeys { it.key.lowercase() }
    private val alphabet: List<Char> = freq.keys.flatMap { it.toList() }.toSortedSet().toList()

    val size: Int get() = freq.size

    fun isKnown(word: String): Boolean = freq.containsKey(word.lowercase())

    fun suggest(
        word: String,
        limit: Int = 5,
    ): List<String> {
        val lowered = word.lowercase()
        if (lowered.isEmpty() || freq.containsKey(lowered)) return emptyList()
        val first = edits1(lowered)
        var found = rank(first)
        if (found.isEmpty() && lowered.length <= MAX_SECOND_PASS_LENGTH) {
            val second = HashSet<String>()
            for (edit in first) second += edits1(edit)
            found = rank(second)
        }
        return found.take(limit)
    }

    fun check(
        text: String,
        suggestions: Int = 3,
    ): List<Misspelling> {
        val problems = mutableListOf<Misspelling>()
        for (word in splitWords(text)) {
            if (word.text.length < 2 || freq.containsKey(word.text)) continue
            if (text.substring(word.start, word.end).any { it.isDigit() }) continue
            problems +=
                Misspelling(
                    start = word.start,
                    end = word.end,
                    word = text.substring(word.start, word.end),
                    suggestions = suggest(word.text, suggestions),
                )
        }
        return problems
    }

    private fun rank(candidates: Set<String>): List<String> =
        candidates
            .filter { freq.containsKey(it) }
            .sortedWith(compareBy<String>({ -(freq.getValue(it)) }, { it }))

    private fun edits1(word: String): Set<String> {
        val edits = HashSet<String>()
        for (i in 0..word.length) {
            val left = word.substring(0, i)
            val right = word.substring(i)
            if (right.isNotEmpty()) {
                edits += left + right.substring(1)
                for (ch in alphabet) edits += left + ch + right.substring(1)
            }
            if (right.length > 1) {
                edits += left + right[1] + right[0] + right.substring(2)
            }
            for (ch in alphabet) edits += left + ch + right
        }
        edits.remove(word)
        return edits
    }

    private companion object {
        const val MAX_SECOND_PASS_LENGTH = 12
    }
}
