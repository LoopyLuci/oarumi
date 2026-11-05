package com.oarumi.app.ui.settings

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.oarumi.app.BuildConfig
import com.oarumi.app.data.apk.ApkExport
import com.oarumi.app.data.packs.PackRepository
import com.oarumi.app.data.update.ApkInstaller
import com.oarumi.app.data.update.UpdateChecker
import com.oarumi.app.data.update.UpdateDownloader
import com.oarumi.app.data.update.UpdatePreferences
import com.oarumi.app.data.update.UpdateScheduler
import com.oarumi.app.data.update.UpdateStatus
import com.oarumi.app.data.update.installedVersion
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import oarumi.lang.PackEntry
import java.io.File
import javax.inject.Inject

data class PackRow(
    val entry: PackEntry,
    val installed: Boolean,
    val busy: Boolean,
)

data class SettingsUiState(
    val versionLabel: String = "",
    val packRows: List<PackRow> = emptyList(),
    val packMessage: String = "",
    val checking: Boolean = false,
    val updateMessage: String = "Not checked yet.",
    val available: UpdateStatus.Available? = null,
    val pendingUpdateVersion: String? = null,
    val autoDownload: Boolean = false,
    val apkMessage: String = "",
)

@HiltViewModel
class SettingsViewModel
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
        private val packs: PackRepository,
        private val checker: UpdateChecker,
        private val downloader: UpdateDownloader,
        private val prefs: UpdatePreferences,
        private val export: ApkExport,
    ) : ViewModel() {
        private val _state =
            MutableStateFlow(
                SettingsUiState(
                    versionLabel = "Version ${installedVersion(BuildConfig.VERSION_NAME)} (${BuildConfig.FLAVOR})",
                    autoDownload = prefs.autoDownload,
                    pendingUpdateVersion = pendingVersion(),
                ),
            )
        val state: StateFlow<SettingsUiState> = _state.asStateFlow()

        private val busyCodes = mutableSetOf<String>()

        init {
            refreshPacks()
        }

        private fun pendingVersion(): String? =
            prefs.pendingVersion?.takeIf {
                File(
                    prefs.pendingApkPath ?: "",
                ).exists()
            }

        private fun refreshPacks() {
            _state.update {
                it.copy(
                    packRows =
                        packs.entries().map { entry ->
                            PackRow(entry, packs.isInstalled(entry), entry.code in busyCodes)
                        },
                )
            }
        }

        // --- language packs -----------------------------------------------

        fun installPack(entry: PackEntry) {
            runPackTask(entry, "Downloading ${entry.name}…", "${entry.name} installed.") { packs.download(entry) }
        }

        fun removePack(entry: PackEntry) {
            packs.remove(entry)
            refreshPacks()
            _state.update { it.copy(packMessage = "${entry.name} removed.") }
        }

        private fun runPackTask(
            entry: PackEntry,
            busyText: String,
            doneText: String,
            work: suspend () -> Unit,
        ) {
            viewModelScope.launch {
                busyCodes += entry.code
                _state.update { it.copy(packMessage = busyText) }
                refreshPacks()
                val message =
                    try {
                        work()
                        doneText
                    } catch (e: Exception) {
                        "Could not install ${entry.name}. ${e.message ?: "Try again."}"
                    }
                busyCodes -= entry.code
                refreshPacks()
                _state.update { it.copy(packMessage = message) }
            }
        }

        // --- app updates ----------------------------------------------------

        fun checkForUpdates() {
            if (_state.value.checking) return
            _state.update { it.copy(checking = true, updateMessage = "Checking GitHub…") }
            viewModelScope.launch {
                try {
                    val status = checker.check(installedVersion(BuildConfig.VERSION_NAME), BuildConfig.FLAVOR)
                    _state.update {
                        it.copy(
                            checking = false,
                            available = status as? UpdateStatus.Available,
                            updateMessage = describe(status),
                        )
                    }
                } catch (e: Exception) {
                    _state.update {
                        it.copy(
                            checking = false,
                            updateMessage = "Could not check for updates. ${e.message ?: ""}".trim(),
                        )
                    }
                }
            }
        }

        private fun describe(status: UpdateStatus): String =
            when (status) {
                is UpdateStatus.UpToDate -> "You have the latest release (${status.latest})."
                is UpdateStatus.Available ->
                    if (status.apk == null) {
                        "Version ${status.release.tag} is out, but it has no APK for this build."
                    } else {
                        "Version ${status.release.tag} is available."
                    }
            }

        fun downloadUpdate() {
            val available = _state.value.available ?: return
            val apk = available.apk ?: return
            _state.update { it.copy(updateMessage = "Downloading ${available.release.tag}…") }
            viewModelScope.launch {
                try {
                    downloader.download(available.release, apk)
                    _state.update {
                        it.copy(
                            pendingUpdateVersion = available.release.tag,
                            updateMessage =
                                "Version ${available.release.tag} is downloaded. " +
                                    "Install it when you are ready.",
                        )
                    }
                } catch (e: Exception) {
                    _state.update { it.copy(updateMessage = e.message ?: "The download failed.") }
                }
            }
        }

        fun setAutoDownload(enabled: Boolean) {
            prefs.autoDownload = enabled
            UpdateScheduler.setEnabled(context, enabled)
            _state.update { it.copy(autoDownload = enabled) }
        }

        /**
         * The system installer intent for the downloaded APK, or the settings
         * screen where the user allows installs from Oarumi first.
         */
        fun installIntent(): Intent? {
            val path = prefs.pendingApkPath
            val apk = path?.let { File(it) }
            if (apk == null || !apk.exists()) {
                _state.update { it.copy(updateMessage = "No downloaded update to install. Download it first.") }
                return null
            }
            if (!ApkInstaller.canInstall(context)) {
                _state.update {
                    it.copy(updateMessage = "Allow installs from Oarumi, then tap Install again.")
                }
                return ApkInstaller.unknownSourcesSettings(context)
            }
            return ApkInstaller.installIntent(context, apk)
        }

        // --- APK --------------------------------------------------------------

        fun suggestedApkName(): String = export.suggestedName()

        fun saveApk(destination: Uri) {
            _state.update { it.copy(apkMessage = "Saving…") }
            viewModelScope.launch {
                val message =
                    try {
                        export.saveTo(destination)
                        "Saved to the location you chose."
                    } catch (e: Exception) {
                        "Could not save the APK. ${e.message ?: ""}".trim()
                    }
                _state.update { it.copy(apkMessage = message) }
            }
        }

        fun shareApk(onReady: (Intent) -> Unit) {
            _state.update { it.copy(apkMessage = "Preparing the APK to share…") }
            viewModelScope.launch {
                try {
                    onReady(export.shareIntent())
                    _state.update { it.copy(apkMessage = "") }
                } catch (e: Exception) {
                    _state.update { it.copy(apkMessage = "Could not prepare the APK. ${e.message ?: ""}".trim()) }
                }
            }
        }
    }
