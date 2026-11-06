package oarumi.lang

/**
 * Word segmentation shared by the spell checker and the language detector.
 *
 * A word is a run of letters and combining marks. Digits, punctuation and
 * whitespace separate words. Mirrors engine/python/oarumi/lang/text.py.
 */
data class Word(
    val start: Int,
    val end: Int,
    val text: String,
)

fun isWordChar(ch: Char): Boolean {
    if (ch.isLetter()) return true
    val type = Character.getType(ch)
    return type == Character.NON_SPACING_MARK.toInt() || type == Character.COMBINING_SPACING_MARK.toInt()
}

fun splitWords(text: String): List<Word> {
    val words = mutableListOf<Word>()
    var start = -1
    for (index in text.indices) {
        if (isWordChar(text[index])) {
            if (start < 0) start = index
        } else if (start >= 0) {
            words += Word(start, index, lowerRun(text, start, index))
            start = -1
        }
    }
    if (start >= 0) words += Word(start, text.length, lowerRun(text, start, text.length))
    return words
}

private fun lowerRun(
    text: String,
    start: Int,
    end: Int,
): String {
    val out = StringBuilder(end - start)
    for (index in start until end) out.append(text[index].lowercaseChar())
    return out.toString()
}
