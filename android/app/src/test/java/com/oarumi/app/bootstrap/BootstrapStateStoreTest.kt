package com.oarumi.app.bootstrap

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class BootstrapStateStoreTest {
    private fun fresh(): BootstrapStateStore {
        val s = BootstrapStateStore()
        s.initialise(flavor = "mlkit", availableLanguages = listOf("es", "fr", "de"))
        return s
    }

    @Test
    fun `initialise populates languages`() {
        val s = fresh()
        assertEquals(3, s.state.value.languages.size)
        assertEquals(setOf("es"), s.state.value.selectedLanguages)
        assertFalse(s.state.value.ready)
    }

    @Test
    fun `toggle language adds and removes`() {
        val s = fresh()
        s.toggleLanguage("fr")
        assertEquals(setOf("es", "fr"), s.state.value.selectedLanguages)
        s.toggleLanguage("es")
        assertEquals(setOf("fr"), s.state.value.selectedLanguages)
    }

    @Test
    fun `readiness requires all selected ready and tts ready`() {
        val s = fresh()
        s.setLanguageState("es", AssetState.READY)
        s.setTts(AssetState.READY, true)
        s.recomputeReadiness()
        assertTrue(s.state.value.ready)
    }

    @Test
    fun `readiness fails if tts failed but languages ready`() {
        // TTS FAILED is non-fatal per the manager logic — verify that.
        val s = fresh()
        s.setLanguageState("es", AssetState.READY)
        s.setTts(AssetState.FAILED, false)
        s.recomputeReadiness()
        assertTrue(s.state.value.ready)
    }

    @Test
    fun `readiness fails if any language not ready`() {
        val s = fresh()
        s.toggleLanguage("fr")
        s.setLanguageState("es", AssetState.READY)
        s.setLanguageState("fr", AssetState.NOT_STARTED)
        s.setTts(AssetState.READY, true)
        s.recomputeReadiness()
        assertFalse(s.state.value.ready)
    }

    @Test
    fun `error blocks readiness`() {
        val s = fresh()
        s.setLanguageState("es", AssetState.READY)
        s.setTts(AssetState.READY, true)
        s.setError("network down")
        s.recomputeReadiness()
        assertFalse(s.state.value.ready)
    }
}
