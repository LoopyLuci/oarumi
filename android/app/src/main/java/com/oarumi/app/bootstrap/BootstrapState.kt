package com.oarumi.app.bootstrap

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

enum class AssetState { NOT_STARTED, DOWNLOADING, READY, FAILED }

data class LanguageStatus(
    val code: String,
    // "mlkit" | "phrasebook"
    val kind: String,
    val state: AssetState = AssetState.NOT_STARTED,
    // 0..1, -1 if indeterminate
    val progress: Float = 0f,
    val error: String? = null,
)

data class TtsStatus(
    val available: Boolean = false,
    val state: AssetState = AssetState.NOT_STARTED,
)

data class BootstrapUiState(
    val flavor: String = "",
    val availableLanguages: List<String> = listOf("es", "fr", "de", "zh", "ar"),
    val selectedLanguages: Set<String> = setOf("es"),
    val languages: List<LanguageStatus> = emptyList(),
    val tts: TtsStatus = TtsStatus(),
    val inProgress: Boolean = false,
    val ready: Boolean = false,
    val error: String? = null,
) {
    val needsBootstrap: Boolean get() = !ready
    val allLanguagesReady: Boolean
        get() = languages.isNotEmpty() && languages.all { it.state == AssetState.READY }
}

/**
 * Holds the single source of truth for bootstrap progress. Updated by
 * BootstrapManager (foreground) and BootstrapWorker (background).
 */
class BootstrapStateStore {
    private val _state = MutableStateFlow(BootstrapUiState())
    val state: StateFlow<BootstrapUiState> = _state.asStateFlow()

    fun initialise(
        flavor: String,
        availableLanguages: List<String>,
    ) {
        _state.update {
            it.copy(
                flavor = flavor,
                availableLanguages = availableLanguages,
                selectedLanguages = it.selectedLanguages.ifEmpty { setOf(availableLanguages.first()) },
                languages =
                    availableLanguages.map { code ->
                        LanguageStatus(
                            code = code,
                            kind = if (flavor == "mlkit") "mlkit" else "phrasebook",
                        )
                    },
            )
        }
    }

    fun toggleLanguage(code: String) {
        _state.update {
            val next =
                if (code in it.selectedLanguages) {
                    it.selectedLanguages - code
                } else {
                    it.selectedLanguages + code
                }
            it.copy(selectedLanguages = next)
        }
    }

    fun setLanguageState(
        code: String,
        state: AssetState,
        progress: Float = 0f,
        error: String? = null,
    ) {
        _state.update { current ->
            current.copy(
                languages =
                    current.languages.map { lang ->
                        if (lang.code == code) {
                            lang.copy(state = state, progress = progress, error = error)
                        } else {
                            lang
                        }
                    },
            )
        }
    }

    fun setTts(
        state: AssetState,
        available: Boolean,
    ) {
        _state.update { it.copy(tts = TtsStatus(available = available, state = state)) }
    }

    fun setInProgress(inProgress: Boolean) = _state.update { it.copy(inProgress = inProgress) }

    fun setError(message: String?) = _state.update { it.copy(error = message) }

    /**
     * Recompute readiness. A build is ready when:
     *  - every selected language is READY
     *  - TTS is either available or explicitly marked FAILED (warn but proceed)
     *  - no error is set
     */
    fun recomputeReadiness() {
        _state.update { current ->
            val selected = current.languages.filter { it.code in current.selectedLanguages }
            val languagesOk =
                selected.isNotEmpty() &&
                    selected.all { it.state == AssetState.READY }
            val ttsOk =
                current.tts.state == AssetState.READY ||
                    current.tts.state == AssetState.FAILED
            val noError = current.error == null
            current.copy(ready = languagesOk && ttsOk && noError)
        }
    }
}
