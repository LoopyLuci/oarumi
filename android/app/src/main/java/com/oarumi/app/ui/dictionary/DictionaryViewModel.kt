package com.oarumi.app.ui.dictionary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import oarumi.db.LanguageStore
import oarumi.db.Lexeme
import javax.inject.Inject

data class DictionaryUiState(
    val query: String = "",
    val results: List<Lexeme> = emptyList(),
    val primes: List<oarumi.db.Prime> = emptyList(),
)

@HiltViewModel
class DictionaryViewModel
    @Inject
    constructor(
        private val store: LanguageStore,
    ) : ViewModel() {
        private val _state = MutableStateFlow(DictionaryUiState())
        val state: StateFlow<DictionaryUiState> = _state.asStateFlow()
        private var searchJob: Job? = null

        init {
            // Room refuses queries on the main thread, so the primes load in the background.
            viewModelScope.launch {
                val primes = withContext(Dispatchers.IO) { store.allPrimes() }
                _state.update { it.copy(primes = primes) }
            }
        }

        fun onQueryChange(query: String) {
            _state.update { it.copy(query = query) }
            // Cancel the search for an older query, so a slow result cannot overwrite a newer one.
            searchJob?.cancel()
            searchJob =
                viewModelScope.launch {
                    val results =
                        if (query.isBlank()) {
                            emptyList()
                        } else {
                            withContext(Dispatchers.IO) { store.searchLexemes(query, limit = 100) }
                        }
                    _state.update { it.copy(results = results) }
                }
        }
    }
