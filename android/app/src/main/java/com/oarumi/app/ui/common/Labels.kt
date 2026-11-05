package com.oarumi.app.ui.common

/**
 * Display names for the codes the engine works with. The UI shows these
 * names and keeps the code as the value, so users never read "es" or "DECL".
 */

private val languageNames =
    mapOf(
        "en" to "English",
        "es" to "Spanish",
        "fr" to "French",
        "de" to "German",
        "zh" to "Mandarin Chinese",
        "ar" to "Arabic",
    )

private val moodNames =
    mapOf(
        "DECL" to "Declarative",
        "INTERR" to "Interrogative",
        "IMPER" to "Imperative",
        "PROM" to "Promissive",
        "EXPRESS" to "Expressive",
        "VOC" to "Vocative",
    )

/** Full English name for a language code. Unknown codes are returned unchanged. */
fun languageName(code: String): String = languageNames[code] ?: code

/** Capitalised label for a target modality code such as "spoken". */
fun modalityName(code: String): String = code.replaceFirstChar { it.uppercase() }

/** Grammatical mood label for an NSM mood code such as "DECL". */
fun moodName(code: String): String = moodNames[code] ?: code
