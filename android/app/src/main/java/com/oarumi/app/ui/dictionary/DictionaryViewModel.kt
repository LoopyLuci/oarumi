package com.oarumi.app.ui.dictionary

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
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
        private val _state =
            MutableStateFlow(
                DictionaryUiState(primes = store.allPrimes()),
            )
        val state: StateFlow<DictionaryUiState> = _state.asStateFlow()

        fun onQueryChange(query: String) {
            _state.update {
                it.copy(
                    query = query,
                    results =
                        if (query.isBlank()) {
                            emptyList()
                        } else {
                            store.searchLexemes(query, limit = 100)
                        },
                )
            }
        }
    }
