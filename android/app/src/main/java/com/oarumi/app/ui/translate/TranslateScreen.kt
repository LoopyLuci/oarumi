package com.oarumi.app.ui.translate

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.ui.common.DegradedBadge
import com.oarumi.app.ui.common.OarumiCard
import com.oarumi.app.ui.common.ScreenHeader
import com.oarumi.app.ui.common.SectionHeader
import com.oarumi.app.ui.common.languageName
import com.oarumi.app.ui.common.modalityName
import com.oarumi.app.ui.common.moodName
import com.oarumi.app.ui.theme.AccentGreen
import com.oarumi.app.ui.theme.BadgeOkFg
import com.oarumi.app.ui.theme.BadgeWarnFg
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary

private val TARGET_MODALITIES = listOf("spoken", "signed", "tactile")

@Composable
fun TranslateScreen(
    onResultReady: (oarumi.types.TranslationResult) -> Unit,
    viewModel: TranslateViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val keyboard = LocalSoftwareKeyboardController.current

    // Fire onResultReady whenever a new result arrives.
    LaunchedEffect(state.result) {
        state.result?.let { onResultReady(it) }
    }

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        ScreenHeader(
            title = "Translate",
            subtitle = "Turn a phrase into Oarumi, then hear it, see it signed, or read it by touch.",
        )

        OarumiCard {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ChoiceDropdown(
                    label = "Source language",
                    options = state.availableLanguages,
                    selected = state.sourceLanguage,
                    display = ::languageName,
                    onSelect = viewModel::selectLanguage,
                    modifier = Modifier.weight(1f),
                )
                ChoiceDropdown(
                    label = "Target modality",
                    options = TARGET_MODALITIES,
                    selected = state.targetModality,
                    display = ::modalityName,
                    onSelect = viewModel::selectModality,
                    modifier = Modifier.weight(1f),
                )
            }

            OutlinedTextField(
                value = state.inputText,
                onValueChange = viewModel::onInputChange,
                label = { Text("Phrase") },
                placeholder = { Text("Type a phrase, for example hola") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                keyboardActions =
                    KeyboardActions(onGo = {
                        keyboard?.hide()
                        viewModel.translate()
                    }),
            )

            Button(
                onClick = {
                    keyboard?.hide()
                    viewModel.translate()
                },
                enabled = !state.isTranslating && state.inputText.isNotBlank(),
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AccentGreen),
            ) {
                Text(
                    text = if (state.isTranslating) "Translating…" else "Translate to Oarumi",
                    style = MaterialTheme.typography.titleMedium,
                )
            }
        }

        state.error?.let { message ->
            Text(
                text = "Translation failed: $message",
                style = MaterialTheme.typography.bodySmall,
                color = BadgeWarnFg,
            )
        }

        ResultPanel(state)

        Text(
            text = state.statusMessage,
            style = MaterialTheme.typography.bodySmall,
            color = TextMuted,
        )
    }
}

@Composable
private fun ResultPanel(state: TranslateUiState) {
    val result = state.result
    OarumiCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text =
                    when {
                        result == null -> "No translation yet"
                        result.degraded -> "Translated with fallback"
                        else -> "Translated"
                    },
                style = MaterialTheme.typography.titleMedium,
                color =
                    when {
                        result == null -> TextMuted
                        result.degraded -> BadgeWarnFg
                        else -> BadgeOkFg
                    },
            )
            Spacer(Modifier.weight(1f))
            DegradedBadge(visible = result?.degraded == true)
        }

        Text(
            text = result?.let { it.surface.surfaceString() } ?: "Your Oarumi sentence will appear here.",
            style = MaterialTheme.typography.headlineSmall.copy(fontSize = 24.sp),
            color = if (result == null) TextMuted else TextPrimary,
        )

        if (result != null) {
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                MetaItem(label = "Mood", value = moodName(result.surface.mood))
                MetaItem(label = "Meaning", value = "${result.pivot.text} (${result.pivot.source})")
                MetaItem(label = "Output", value = result.modalities.keys.joinToString { modalityName(it) })
            }

            SectionHeader("Details")
            Text(
                text = state.formattedOutput,
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
                color = TextPrimary,
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(SurfaceInset)
                        .padding(12.dp)
                        .horizontalScroll(rememberScrollState()),
            )

            if (state.traceLines.isNotEmpty()) {
                SectionHeader("Trace")
                Column(
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .background(SurfaceInset)
                            .padding(12.dp),
                ) {
                    state.traceLines.forEach { line ->
                        Text(
                            text = line,
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            color = TextSecondary,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MetaItem(
    label: String,
    value: String,
) {
    Column {
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 10.sp),
            color = TextMuted,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyLarge,
            color = TextPrimary,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChoiceDropdown(
    label: String,
    options: List<String>,
    selected: String,
    display: (String) -> String,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
        modifier = modifier,
    ) {
        OutlinedTextField(
            value = display(selected),
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = {
                ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
            },
            modifier =
                Modifier
                    .menuAnchor()
                    .fillMaxWidth(),
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(display(option)) },
                    onClick = {
                        onSelect(option)
                        expanded = false
                    },
                )
            }
        }
    }
}
