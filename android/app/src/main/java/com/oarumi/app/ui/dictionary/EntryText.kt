package com.oarumi.app.ui.dictionary

import oarumi.db.Lexeme
import oarumi.db.Prime
import oarumi.db.Sense
import oarumi.db.Sign

/*
 * One-sentence descriptions of each entry part, read aloud by screen readers in place of the
 * visible text, which is split across several labels. Statuses use formStatusLabel, so a
 * placeholder is announced as pending, never as a word or a sign.
 */

fun lexemeSummary(lx: Lexeme): String {
    val click = if (lx.click != null) ", click ${lx.click}" else ""
    return "${lx.phonForm}$click, meaning ${lx.gloss}, ${lx.rootClass}, frequency ${lx.frequency}, " +
        formStatusLabel(lx.formStatus)
}

fun primeSummary(p: Prime): String = "Prime ${p.id}, meaning ${p.gloss}, spoken form ${formStatusLabel(p.formStatus)}"

fun senseSummary(sense: Sense): String {
    val primes = if (sense.primes.isEmpty()) "none yet" else sense.primes.joinToString(" ")
    return "Sense ${sense.senseNo}, ${sense.gloss}. Primes: $primes, ${formStatusLabel(sense.decompStatus)}"
}

fun signSummary(sign: Sign): String {
    val hamnosys = sign.hamnosys.ifBlank { "not set" }
    return "Sign, HamNoSys $hamnosys, ${formStatusLabel(sign.formStatus)}"
}
