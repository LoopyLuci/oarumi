package com.oarumi.app.bootstrap

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.ui.theme.AccentGreen
import com.oarumi.app.ui.theme.BadgeOkFg
import com.oarumi.app.ui.theme.BadgeWarnFg
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary

@Composable
fun BootstrapWizard(
    onReady: () -> Unit,
    viewModel: BootstrapViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // When the manager reports ready, notify the caller.
    androidx.compose.runtime.LaunchedEffect(state.ready) {
        if (state.ready) onReady()
    }

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .background(SurfaceInset)
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = "Welcome to Oarumi",
            style = MaterialTheme.typography.displayLarge,
            color = TextPrimary,
        )
        Text(
            text =
                "Oarumi works fully offline after a one-time setup. " +
                    "Select the source languages you need and the app will download " +
                    "the required models.",
            style = MaterialTheme.typography.bodyLarge,
            color = TextSecondary,
        )

        Text(
            text = "Build: ${state.flavor}",
            style = MaterialTheme.typography.labelSmall,
            fontFamily = FontFamily.Monospace,
            color = TextMuted,
        )

        if (state.flavor == "mlkit") {
            Text(
                text = "Source languages",
                style = MaterialTheme.typography.titleMedium,
                color = TextPrimary,
            )
            state.languages.forEach { lang ->
                LanguageRow(
                    status = lang,
                    selected = lang.code in state.selectedLanguages,
                    enabled = !state.inProgress,
                    onToggle = { viewModel.toggleLanguage(lang.code) },
                )
            }
            Text(
                text = "Each language model is roughly 30 MB. Select only the languages you plan to use.",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted,
            )
        } else {
            Text(
                text = "This build ships with the phrasebook backend. Everything is bundled; no downloads required.",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted,
            )
        }

        // TTS status
        TtsRow(tts = state.tts, inProgress = state.inProgress, onInstallTts = viewModel::openTtsInstaller)

        if (state.error != null) {
            Text(
                text = "Error: ${state.error}",
                style = MaterialTheme.typography.bodySmall,
                color = BadgeWarnFg,
            )
        }

        if (state.inProgress) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
                Text("Downloading…", style = MaterialTheme.typography.bodySmall, color = TextSecondary)
            }
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }

        Button(
            onClick = { viewModel.startBootstrap() },
            enabled = !state.inProgress && state.selectedLanguages.isNotEmpty(),
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(48.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AccentGreen),
        ) {
            Text(if (state.inProgress) "Setting up…" else "Start setup")
        }

        if (state.flavor == "mlkit") {
            OutlinedButton(
                onClick = viewModel::continueInBackground,
                enabled = !state.inProgress,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Continue in background")
            }
        }
    }
}

@Composable
private fun LanguageRow(
    status: LanguageStatus,
    selected: Boolean,
    enabled: Boolean,
    onToggle: () -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(MaterialTheme.colorScheme.surface)
                .toggleable(
                    value = selected,
                    enabled = enabled,
                    onValueChange = { onToggle() },
                )
                .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            imageVector =
                when (status.state) {
                    AssetState.READY -> Icons.Filled.CheckCircle
                    AssetState.FAILED -> Icons.Filled.Error
                    AssetState.DOWNLOADING -> Icons.Filled.CheckCircle
                    AssetState.NOT_STARTED -> Icons.Filled.RadioButtonUnchecked
                },
            contentDescription = null,
            tint =
                when (status.state) {
                    AssetState.READY -> BadgeOkFg
                    AssetState.FAILED -> BadgeWarnFg
                    AssetState.DOWNLOADING -> MaterialTheme.colorScheme.primary
                    AssetState.NOT_STARTED -> TextMuted
                },
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = status.code,
                style = MaterialTheme.typography.titleMedium,
                color = TextPrimary,
            )
            Text(
                text = status.kind,
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
                color = TextMuted,
            )
        }
        if (status.state == AssetState.DOWNLOADING) {
            CircularProgressIndicator(modifier = Modifier.size(18.dp))
        }
    }
}

@Composable
private fun TtsRow(
    tts: TtsStatus,
    inProgress: Boolean,
    onInstallTts: () -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(MaterialTheme.colorScheme.surface)
                .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            imageVector =
                when (tts.state) {
                    AssetState.READY -> Icons.Filled.CheckCircle
                    AssetState.FAILED -> Icons.Filled.Error
                    AssetState.DOWNLOADING -> Icons.Filled.CheckCircle
                    AssetState.NOT_STARTED -> Icons.Filled.RadioButtonUnchecked
                },
            contentDescription = null,
            tint =
                when (tts.state) {
                    AssetState.READY -> BadgeOkFg
                    AssetState.FAILED -> BadgeWarnFg
                    AssetState.DOWNLOADING -> MaterialTheme.colorScheme.primary
                    AssetState.NOT_STARTED -> TextMuted
                },
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Text-to-speech",
                style = MaterialTheme.typography.titleMedium,
                color = TextPrimary,
            )
            Text(
                text =
                    when (tts.state) {
                        AssetState.READY -> "Available"
                        AssetState.FAILED -> "Not available on this device (spoken output will be silent)"
                        AssetState.DOWNLOADING -> "Checking…"
                        AssetState.NOT_STARTED -> "Will be checked during setup"
                    },
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
                color = TextMuted,
            )
        }
        if (tts.state == AssetState.FAILED && !inProgress) {
            OutlinedButton(onClick = onInstallTts) { Text("Install") }
        }
    }
}
