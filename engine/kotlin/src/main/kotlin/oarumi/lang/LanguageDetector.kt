package oarumi.lang

import kotlin.math.exp
import kotlin.math.ln

/** Result of [LanguageDetector.detect]. `code` is null when the model is unsure. */
data class Detection(
    val code: String?,
    val confidence: Double,
    val ranking: List<Pair<String, Double>>,
)

/**
 * Character n-gram language detection over the installed packs. Mirrors
 * engine/python/oarumi/lang/detect.py, including the probability floor for
 * unseen n-grams, the dictionary bonus, and the margin rule.
 */
class LanguageDetector(
    profiles: Map<String, Map<String, Int>>,
    private val dictionaries: Map<String, Map<String, Int>> = emptyMap(),
) {
    private class Model(
        val probabilities: Map<String, Double>,
        val floor: Double,
    )

    private val models: Map<String, Model>

    init {
        val built = LinkedHashMap<String, Model>()
        for (code in profiles.keys.sorted()) {
            val counts = profiles.getValue(code)
            val total = counts.values.sumOf { it.toLong() }
            if (total <= 0L) continue
            val probabilities =
                counts.toSortedMap().mapValues { (_, count) -> count.toDouble() / total.toDouble() }
            val floor = 0.5 * probabilities.values.minOf { it }
            built[code] = Model(probabilities, floor)
        }
        models = built
    }

    val languages: List<String> get() = models.keys.toList()

    fun detect(text: String): Detection {
        val grams = ngrams(text)
        if (grams.isEmpty() || models.size < 2) return Detection(null, 0.0, emptyList())
        val words = splitWords(text).map { it.text }
        val sortedGrams = grams.toSortedMap()

        val scores = mutableListOf<Pair<String, Double>>()
        for ((code, model) in models) {
            var total = 0.0
            for ((gram, count) in sortedGrams) {
                total += count * ln(model.probabilities[gram] ?: model.floor)
            }
            val dictionary = dictionaries[code]
            if (dictionary != null) {
                total += WORD_BONUS * words.count { dictionary.containsKey(it) }
            }
            scores += code to total
        }
        scores.sortWith(compareBy<Pair<String, Double>>({ -it.second }, { it.first }))

        val best = scores[0].second
        val runnerUp = scores[1].second
        var normaliser = 0.0
        for ((_, score) in scores) normaliser += exp(score - best)
        val share = 1.0 / normaliser
        val code = if (best - runnerUp >= MIN_MARGIN) scores[0].first else null
        return Detection(code = code, confidence = share, ranking = scores)
    }

    companion object {
        const val MIN_MARGIN = 2.0
        const val WORD_BONUS = 8.0

        /** Collapse syllable blocks onto one representative, as langdetect's profiles expect. */
        fun fold(ch: Char): Char {
            val code = ch.code
            return when (code) {
                in 0xAC00..0xD7A3 -> '가'
                in 0x3040..0x309F -> 'あ'
                in 0x30A0..0x30FF -> 'ア'
                else -> ch
            }
        }

        fun ngrams(text: String): Map<String, Int> {
            val counts = HashMap<String, Int>()
            for (word in splitWords(text)) {
                val padded = " " + word.text.map { fold(it) }.joinToString("") + " "
                for (size in 1..3) {
                    for (index in 0..(padded.length - size)) {
                        val gram = padded.substring(index, index + size)
                        if (size == 1 && gram == " ") continue
                        counts[gram] = (counts[gram] ?: 0) + 1
                    }
                }
            }
            return counts
        }
    }
}
