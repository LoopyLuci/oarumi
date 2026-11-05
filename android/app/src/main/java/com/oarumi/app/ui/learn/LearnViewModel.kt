package com.oarumi.app.ui.learn

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
import oarumi.db.LanguageStore
import oarumi.db.Prime
import javax.inject.Inject

data class LearnUiState(
    val primes: List<Prime> = emptyList(),
    val index: Int = 0,
) {
    val current: Prime? get() = primes.getOrNull(index)
}

@HiltViewModel
class LearnViewModel
    @Inject
    constructor(store: LanguageStore) : ViewModel() {
        private val _state = MutableStateFlow(LearnUiState())
        val state: StateFlow<LearnUiState> = _state.asStateFlow()

        init {
            // Room refuses queries on the main thread, so the primes load in the background.
            viewModelScope.launch {
                val primes = withContext(Dispatchers.IO) { store.allPrimes() }
                _state.update { it.copy(primes = primes) }
            }
        }

        fun next() =
            _state.update {
                if (it.primes.isEmpty()) {
                    it
                } else {
                    it.copy(index = (it.index + 1) % it.primes.size)
                }
            }

        fun previous() =
            _state.update {
                if (it.primes.isEmpty()) {
                    it
                } else {
                    it.copy(index = (it.index - 1 + it.primes.size) % it.primes.size)
                }
            }
    }
