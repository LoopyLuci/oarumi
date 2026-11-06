package com.oarumi.app.ui.dictionary

/**
 * Label for a form or decomposition status (docs/DICTIONARY.md). Anything that is not
 * signed off or provisional is shown as pending, so an unknown value never reads as approved.
 */
fun formStatusLabel(status: String): String =
    when (status) {
        "signed_off" -> "signed off"
        "provisional" -> "provisional"
        else -> "pending linguist sign-off"
    }
