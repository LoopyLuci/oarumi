package com.oarumi.app.ui.settings

import android.Manifest
import android.content.Intent
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.data.update.ApkInstaller
import com.oarumi.app.ui.common.OarumiCard
import com.oarumi.app.ui.common.ScreenHeader
import com.oarumi.app.ui.theme.AccentGreen
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    val saveLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument(ApkInstaller.APK_MIME)) { uri ->
            if (uri != null) viewModel.saveApk(uri)
        }
    val notificationLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { _ -> }

    Column(
        modifier =
            androidx.compose.ui.Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        ScreenHeader(
            title = "Settings",
            subtitle = "Language packs, app updates, and the APK.",
        )

        OarumiCard {
            SettingsSection(title = "Language packs") {
                Text(
                    text =
                        "Spelling and detection data. Base packs are built in. " +
                            "Extra packs download once and then work offline.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextMuted,
                )
                state.packRows.forEach { row ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(text = row.entry.name, style = MaterialTheme.typography.bodyLarge, color = TextPrimary)
                            Text(
                                text = packStatus(row.entry.base, row.installed, row.entry.spell, row.entry.sizeBytes),
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted,
                            )
                        }
                        if (row.installed && !row.entry.base) {
                            OutlinedButton(
                                onClick = { viewModel.removePack(row.entry) },
                                enabled = !row.busy,
                            ) { Text("Remove") }
                        } else if (!row.installed) {
                            Button(
                                onClick = { viewModel.installPack(row.entry) },
                                enabled = !row.busy,
                                colors =
                                    androidx.compose.material3.ButtonDefaults.buttonColors(
                                        containerColor = AccentGreen,
                                    ),
                            ) { Text(if (row.busy) "Downloading…" else "Install") }
                        }
                    }
                }
                if (state.packMessage.isNotBlank()) {
                    Text(text = state.packMessage, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                }
            }
        }

        OarumiCard {
            SettingsSection(title = "App updates") {
                Text(text = state.versionLabel, style = MaterialTheme.typography.bodyLarge, color = TextPrimary)
                Button(
                    onClick = viewModel::checkForUpdates,
                    enabled = !state.checking,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(if (state.checking) "Checking…" else "Check for updates") }
                Text(text = state.updateMessage, style = MaterialTheme.typography.bodySmall, color = TextSecondary)

                val available = state.available
                if (available?.apk != null && state.pendingUpdateVersion == null) {
                    OutlinedButton(onClick = viewModel::downloadUpdate, modifier = Modifier.fillMaxWidth()) {
                        Text("Download update")
                    }
                }
                if (state.pendingUpdateVersion != null) {
                    Button(
                        onClick = {
                            viewModel.installIntent()?.let { intent -> context.startActivity(intent) }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = AccentGreen),
                    ) { Text("Install update ${state.pendingUpdateVersion}") }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Download updates in the background",
                            style = MaterialTheme.typography.bodyLarge,
                            color = TextPrimary,
                        )
                        Text(
                            text =
                                "Checks about every 12 hours on a network and downloads a verified APK. " +
                                    "Android still asks you to confirm the install.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted,
                        )
                    }
                    Switch(
                        checked = state.autoDownload,
                        onCheckedChange = { enabled ->
                            if (enabled && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                                notificationLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                            }
                            viewModel.setAutoDownload(enabled)
                        },
                    )
                }
            }
        }

        OarumiCard {
            SettingsSection(title = "APK") {
                Text(
                    text = "Save the APK this app was installed from, or share it with another device.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextMuted,
                )
                OutlinedButton(
                    onClick = { saveLauncher.launch(viewModel.suggestedApkName()) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Save APK to device") }
                Button(
                    onClick = {
                        viewModel.shareApk { intent ->
                            context.startActivity(Intent.createChooser(intent, "Share Oarumi APK"))
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Share APK") }
                if (state.apkMessage.isNotBlank()) {
                    Text(text = state.apkMessage, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                }
            }
        }
    }
}

@Composable
private fun SettingsSection(
    title: String,
    content: @Composable () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(text = title, style = MaterialTheme.typography.titleMedium, color = TextPrimary)
        content()
    }
}

private fun packStatus(
    base: Boolean,
    installed: Boolean,
    spell: Boolean,
    sizeBytes: Long,
): String {
    val includes = if (spell) "Spelling and detection" else "Detection"
    val state =
        when {
            base && installed -> "Built in"
            installed -> "Installed"
            else -> "Not installed"
        }
    return "$state · $includes · ${sizeBytes / 1024} KB"
}
