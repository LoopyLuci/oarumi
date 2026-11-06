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
import oarumi.db.Prime
import javax.inject.Inject

/** Browse filters. [rootClass] is null for All and for Primes, which lists the NSM inventory instead. */
enum class DictionaryFilter(
    val label: String,
    val rootClass: String?,
) {
    All("All", null),
    Nouns("Nouns", "noun"),
    Verbs("Verbs", "verb"),
    Modifiers("Modifiers", "modifier"),
    Particles("Particles", "particle"),
    Primes("Primes", null),
}

data class DictionaryUiState(
    val query: String = "",
    val filter: DictionaryFilter = DictionaryFilter.All,
    /** Lexemes for the query and filter, or the browse list when the query is blank. */
    val results: List<Lexeme> = emptyList(),
    /** Every NSM prime, loaded once. */
    val primes: List<Prime> = emptyList(),
    /** Lexeme count per root class, for the filter labels. */
    val rootCounts: Map<String, Int> = emptyMap(),
) {
    /** The primes to show: only under the Primes filter, matched against the query. */
    val visiblePrimes: List<Prime>
        get() = if (filter == DictionaryFilter.Primes) matchPrimes(primes, query) else emptyList()
}

/** Case-insensitive substring match on the prime ID, gloss and spoken form. A blank query matches all. */
fun matchPrimes(
    primes: List<Prime>,
    query: String,
): List<Prime> {
    val needle = query.trim()
    if (needle.isEmpty()) return primes
    return primes.filter { p ->
        listOf(p.id, p.gloss, p.spokenForm).any { it.contains(needle, ignoreCase = true) }
    }
}

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
            // Room refuses queries on the main thread, so the loads run in the background.
            viewModelScope.launch {
                val (primes, counts) =
                    withContext(Dispatchers.IO) { store.allPrimes() to store.rootClassCounts() }
                _state.update { it.copy(primes = primes, rootCounts = counts) }
            }
            refreshResults()
        }

        fun onQueryChange(query: String) {
            _state.update { it.copy(query = query) }
            refreshResults()
        }

        fun onFilterChange(filter: DictionaryFilter) {
            _state.update { it.copy(filter = filter) }
            refreshResults()
        }

        private fun refreshResults() {
            // Cancel the load for an older query or filter, so a slow result cannot overwrite a newer one.
            searchJob?.cancel()
            val current = _state.value
            searchJob =
                viewModelScope.launch {
                    val results =
                        if (current.filter == DictionaryFilter.Primes) {
                            emptyList()
                        } else {
                            withContext(Dispatchers.IO) {
                                if (current.query.isBlank()) {
                                    store.browseLexemes(current.filter.rootClass, limit = BROWSE_LIMIT)
                                } else {
                                    store.searchLexemes(
                                        current.query,
                                        limit = SEARCH_LIMIT,
                                        rootClass = current.filter.rootClass,
                                    )
                                }
                            }
                        }
                    _state.update { it.copy(results = results) }
                }
        }

        private companion object {
            const val BROWSE_LIMIT = 500
            const val SEARCH_LIMIT = 100
        }
    }
