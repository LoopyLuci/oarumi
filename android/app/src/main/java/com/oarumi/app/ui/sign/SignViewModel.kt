package com.oarumi.app.ui.sign

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonPrimitive
import oarumi.types.TranslationResult
import javax.inject.Inject

data class SignUiState(
    val sigml: String? = null,
    val gloss: String? = null,
    val hint: String = "Run a translation with target modality = signed.",
    val canPlay: Boolean = false,
)

@HiltViewModel
class SignViewModel
    @Inject
    constructor() : ViewModel() {
        private val _state = MutableStateFlow(SignUiState())
        val state: StateFlow<SignUiState> = _state.asStateFlow()

        fun updateFromResult(result: TranslationResult) {
            val payload = result.modalities["signed"] ?: return
            val sigml = (payload["sigml"] as? JsonPrimitive)?.content ?: return
            val gloss = (payload["gloss"] as? JsonPrimitive)?.content ?: "?"
            _state.update {
                it.copy(
                    sigml = sigml,
                    gloss = gloss,
                    hint = "Last result ready ($gloss). Press Play.",
                    canPlay = sigml.isNotBlank(),
                )
            }
        }

        fun updateFromSigml(sigml: String) {
            val gloss = state.value.gloss ?: "?"
            _state.update {
                it.copy(
                    sigml = sigml,
                    hint = "Last result ready ($gloss). Press Play.",
                    canPlay = sigml.isNotBlank(),
                )
            }
        }

        fun replay() {
            val current = _state.value
            if (current.sigml.isNullOrBlank()) return
            // Toggle: set to null then back, so the LaunchedEffect in the Composable
            // re-runs. Alternatively, the Composable watches a separate trigger.
            _state.update { it.copy(sigml = it.sigml) }
        }

        @Suppress("unused")
        private suspend fun noop() = viewModelScope.launch { }
    }
