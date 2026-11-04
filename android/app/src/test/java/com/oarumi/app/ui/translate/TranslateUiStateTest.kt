package com.oarumi.app.ui.translate

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TranslateUiStateTest {
    @Test
    fun `initial state has defaults`() {
        val s = TranslateUiState()
        assertEquals("es", s.sourceLanguage)
        assertEquals("spoken", s.targetModality)
        assertEquals("", s.inputText)
        assertEquals(false, s.isTranslating)
        assertEquals(null, s.result)
        assertEquals(false, s.showDegraded)
    }

    @Test
    fun `language changes propagate`() {
        val s = TranslateUiState().copy(sourceLanguage = "fr", targetModality = "signed")
        assertEquals("fr", s.sourceLanguage)
        assertEquals("signed", s.targetModality)
    }

    @Test
    fun `formatted output is empty without result`() {
        assertTrue(TranslateUiState().formattedOutput.isEmpty())
        assertTrue(TranslateUiState().traceLines.isEmpty())
    }
}
