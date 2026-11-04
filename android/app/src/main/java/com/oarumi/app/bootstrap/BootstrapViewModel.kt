package com.oarumi.app.bootstrap

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.WorkManager
import com.oarumi.app.data.pivot.FlavorPivot
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

@HiltViewModel
class BootstrapViewModel
    @Inject
    constructor(
        private val manager: BootstrapManager,
        private val stateStore: BootstrapStateStore,
        private val workManager: WorkManager,
    ) : ViewModel() {
        val state: StateFlow<BootstrapUiState> = stateStore.state

        init {
            viewModelScope.launch(Dispatchers.IO) {
                stateStore.initialise(
                    flavor = FlavorPivot.name,
                    availableLanguages = manager.availableLanguages(),
                )
                manager.isReady()
            }
        }

        fun toggleLanguage(code: String) = stateStore.toggleLanguage(code)

        fun startBootstrap() {
            viewModelScope.launch {
                manager.startBootstrap()
            }
        }

        fun continueInBackground() {
            androidx.work.OneTimeWorkRequestBuilder<BootstrapWorker>()
                .build()
                .let { workManager.enqueue(it) }
        }

        fun openTtsInstaller() = manager.openTtsInstaller()

        @Suppress("unused")
        private suspend fun unusedIo() = withContext(Dispatchers.IO) { Unit }
    }
