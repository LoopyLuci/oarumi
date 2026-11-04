package com.oarumi.app.ui.translate

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import oarumi.pipeline.Pipeline
import oarumi.reliability.AuditLog
import oarumi.types.TranslationRequest
import javax.inject.Inject

@HiltViewModel
class TranslateViewModel
    @Inject
    constructor(
        private val pipeline: Pipeline,
        private val audit: AuditLog,
    ) : ViewModel() {
        private val _state = MutableStateFlow(TranslateUiState())
        val state: StateFlow<TranslateUiState> = _state.asStateFlow()

        fun selectLanguage(code: String) = _state.update { it.copy(sourceLanguage = code) }

        fun selectModality(modality: String) = _state.update { it.copy(targetModality = modality) }

        fun onInputChange(text: String) = _state.update { it.copy(inputText = text) }

        fun translate() {
            val current = _state.value
            if (current.inputText.isBlank()) {
                _state.update { it.copy(statusMessage = "Enter some text first.") }
                return
            }
            _state.update { it.copy(isTranslating = true, statusMessage = "Translating…", error = null) }

            viewModelScope.launch {
                val req =
                    TranslationRequest(
                        text = current.inputText.trim(),
                        lang = current.sourceLanguage,
                        modality = current.targetModality,
                    )
                try {
                    val result =
                        withContext(Dispatchers.Default) {
                            pipeline.translate(req)
                        }
                    _state.update {
                        it.copy(
                            isTranslating = false,
                            result = result,
                            statusMessage = if (result.degraded) "Translated (degraded)." else "Translated.",
                        )
                    }
                } catch (e: Exception) {
                    _state.update {
                        it.copy(
                            isTranslating = false,
                            error = e.message ?: "Unknown error",
                            statusMessage = "Translation failed.",
                        )
                    }
                }
            }
        }

        fun auditTail(maxLines: Int = 3): String {
            val path = audit.path
            if (!java.nio.file.Files.exists(path)) return "(no audit events yet)"
            return try {
                val lines =
                    java.nio.file.Files.readAllLines(path)
                        .filter { it.isNotBlank() }
                        .takeLast(maxLines)
                if (lines.isEmpty()) return "(no audit events yet)"
                lines.joinToString("  ·  ") { line ->
                    runCatching {
                        val obj = Json.parseToJsonElement(line).jsonObject
                        val component = (obj["component"] as? JsonPrimitive)?.content ?: "?"
                        val event = (obj["event"] as? JsonPrimitive)?.content ?: "?"
                        "$component:$event"
                    }.getOrDefault("?")
                }
            } catch (e: Exception) {
                "(audit unreadable: ${e.message})"
            }
        }
    }
