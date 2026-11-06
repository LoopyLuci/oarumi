package com.oarumi.app.ui.translate

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.oarumi.app.data.packs.PackRepository
import com.oarumi.app.ui.common.languageName
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import oarumi.lang.Misspelling
import oarumi.pipeline.Pipeline
import oarumi.reliability.AuditLog
import oarumi.types.TranslationRequest
import javax.inject.Inject
import kotlin.math.roundToInt

@HiltViewModel
class TranslateViewModel
    @Inject
    constructor(
        private val pipeline: Pipeline,
        private val audit: AuditLog,
        private val packs: PackRepository,
    ) : ViewModel() {
        private val _state = MutableStateFlow(TranslateUiState())
        val state: StateFlow<TranslateUiState> = _state.asStateFlow()

        private var spellJob: Job? = null

        fun selectLanguage(code: String) {
            _state.update { it.copy(sourceLanguage = code) }
            scheduleSpellCheck()
        }

        fun selectModality(modality: String) = _state.update { it.copy(targetModality = modality) }

        fun onInputChange(text: String) {
            _state.update { it.copy(inputText = text) }
            scheduleSpellCheck()
        }

        /** Waits for a pause in typing, then checks spelling against the installed dictionary. */
        private fun scheduleSpellCheck() {
            spellJob?.cancel()
            spellJob =
                viewModelScope.launch {
                    delay(SPELL_DEBOUNCE_MS)
                    val current = _state.value
                    val hints = withContext(Dispatchers.IO) { spellHints(current.sourceLanguage, current.inputText) }
                    _state.update { it.copy(spellHints = hints) }
                }
        }

        private fun spellHints(
            lang: String,
            text: String,
        ): List<Misspelling> {
            if (lang == AUTO_LANGUAGE || text.isBlank()) return emptyList()
            return packs.spellChecker(lang)?.check(text)?.take(MAX_SPELL_HINTS) ?: emptyList()
        }

        fun translate() {
            val current = _state.value
            if (current.inputText.isBlank()) {
                _state.update { it.copy(statusMessage = "Enter some text first.") }
                return
            }
            _state.update { it.copy(isTranslating = true, statusMessage = "Translating…", error = null) }

            viewModelScope.launch {
                val text = current.inputText.trim()
                var lang = current.sourceLanguage
                var detectedNote = ""
                if (lang == AUTO_LANGUAGE) {
                    val detection = withContext(Dispatchers.IO) { packs.detector().detect(text) }
                    val detected = detection.code
                    if (detected == null) {
                        _state.update {
                            it.copy(
                                isTranslating = false,
                                statusMessage = "Could not tell the language. Choose a source language.",
                            )
                        }
                        return@launch
                    }
                    lang = detected
                    val percent = (detection.confidence * 100).roundToInt()
                    detectedNote = "Detected ${languageName(detected)} ($percent%). "
                }
                val req =
                    TranslationRequest(
                        text = text,
                        lang = lang,
                        modality = current.targetModality,
                    )
                try {
                    val result =
                        withContext(Dispatchers.Default) {
                            pipeline.translate(req)
                        }
                    val outcome = if (result.degraded) "Translated (degraded)." else "Translated."
                    _state.update {
                        it.copy(
                            isTranslating = false,
                            result = result,
                            statusMessage = detectedNote + outcome,
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

        private companion object {
            const val SPELL_DEBOUNCE_MS = 350L
            const val MAX_SPELL_HINTS = 4
        }
    }
