package com.oarumi.app.ui.dictionary

import oarumi.db.Lexeme
import oarumi.db.Prime
import oarumi.db.Sense
import oarumi.db.Sign
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class EntryTextTest {
    private val lexeme = Lexeme(1, "manu", null, null, "who", "noun", 900, "provisional")

    @Test
    fun `status labels never read an unknown value as approved`() {
        assertEquals("signed off", formStatusLabel("signed_off"))
        assertEquals("provisional", formStatusLabel("provisional"))
        assertEquals("pending linguist sign-off", formStatusLabel("placeholder"))
        assertEquals("pending linguist sign-off", formStatusLabel(""))
        assertEquals("pending linguist sign-off", formStatusLabel("approved"))
    }

    @Test
    fun `lexeme summary names the headword, meaning, class and status`() {
        assertEquals(
            "manu, meaning who, noun, frequency 900, provisional",
            lexemeSummary(lexeme),
        )
    }

    @Test
    fun `lexeme summary announces a click form`() {
        val clicked = lexeme.copy(phonForm = "ʘa", click = "ʘ", gloss = "here")
        assertTrue(lexemeSummary(clicked).startsWith("ʘa, click ʘ, meaning here"))
    }

    @Test
    fun `prime summary says a placeholder spoken form is pending`() {
        val prime = Prime("SOMEONE", "someone", "substantives", listOf("substance"), "someone", "s", "t", "v")
        val text = primeSummary(prime)
        assertTrue(text.contains("pending linguist sign-off"))
        assertFalse(text.contains("signed off"))
    }

    @Test
    fun `sense summary says when no primes are recorded yet`() {
        val sense = Sense(1, 1, 1, "to talk", emptyList(), "placeholder")
        assertEquals(
            "Sense 1, to talk. Primes: none yet, pending linguist sign-off",
            senseSummary(sense),
        )
    }

    @Test
    fun `sense summary lists the primes in order`() {
        val sense = Sense(2, 2, 1, "liquid", listOf("SOMEONE", "DO"), "signed_off")
        assertEquals("Sense 1, liquid. Primes: SOMEONE DO, signed off", senseSummary(sense))
    }

    @Test
    fun `sign summary says an unset HamNoSys is not set`() {
        val sign = Sign(1, 1, "", "{}", "placeholder")
        assertEquals("Sign, HamNoSys not set, pending linguist sign-off", signSummary(sign))
    }
}
