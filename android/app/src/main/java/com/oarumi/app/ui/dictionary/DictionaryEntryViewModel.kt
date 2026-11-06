package com.oarumi.app.ui.dictionary

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.oarumi.app.ui.nav.DictionaryEntryRoute
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import oarumi.db.LanguageStore
import oarumi.db.Lexeme
import oarumi.db.Sense
import oarumi.db.Sign
import javax.inject.Inject

data class EntryUiState(
    /** Null when the lexeme does not exist, or before the load finishes. */
    val lexeme: Lexeme? = null,
    val senses: List<Sense> = emptyList(),
    val signs: List<Sign> = emptyList(),
    val loaded: Boolean = false,
)

/** Loads one dictionary entry. The lexeme ID comes from the navigation argument [DictionaryEntryRoute.ARG]. */
@HiltViewModel
class DictionaryEntryViewModel
    @Inject
    constructor(
        private val store: LanguageStore,
        savedStateHandle: SavedStateHandle,
    ) : ViewModel() {
        private val _state = MutableStateFlow(EntryUiState())
        val state: StateFlow<EntryUiState> = _state.asStateFlow()

        init {
            val lexemeId = checkNotNull(savedStateHandle.get<Int>(DictionaryEntryRoute.ARG))
            viewModelScope.launch {
                val entry =
                    withContext(Dispatchers.IO) {
                        store.getLexeme(lexemeId)?.let { lx ->
                            EntryUiState(
                                lexeme = lx,
                                senses = store.sensesFor(lexemeId),
                                signs = store.signsFor(lexemeId),
                            )
                        }
                    }
                _state.value = (entry ?: EntryUiState()).copy(loaded = true)
            }
        }
    }
