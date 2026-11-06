package com.oarumi.app.ui.dictionary

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary
import oarumi.db.Sense
import oarumi.db.Sign

/** One dictionary entry: its headword, senses with prime decompositions, and signs. */
@Composable
fun DictionaryEntryScreen(
    onBack: () -> Unit,
    viewModel: DictionaryEntryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val lexeme = state.lexeme

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TextButton(onClick = onBack) { Text("Back to dictionary") }

        when {
            !state.loaded -> Text("Loading…", color = TextSecondary)
            lexeme == null -> Text("This word is not in the dictionary.", color = TextSecondary)
            else -> {
                val click = if (lexeme.click != null) " [${lexeme.click}]" else ""
                Text(
                    text = "${lexeme.phonForm}$click",
                    style = MaterialTheme.typography.headlineMedium,
                    color = TextPrimary,
                    modifier = Modifier.semantics { heading() },
                )
                Text(
                    text = lexeme.gloss,
                    style = MaterialTheme.typography.titleMedium,
                    color = TextSecondary,
                )
                Text(
                    text = "root class ${lexeme.rootClass}  ·  frequency ${lexeme.frequency}  ·  ${formStatusLabel(
                        lexeme.formStatus,
                    )}",
                    style = MaterialTheme.typography.labelSmall,
                    fontFamily = FontFamily.Monospace,
                    color = TextSecondary,
                )

                SectionTitle("Senses")
                if (state.senses.isEmpty()) {
                    Text("No senses recorded yet.", style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                }
                state.senses.forEach { SenseCard(it) }

                SectionTitle("Signs")
                if (state.signs.isEmpty()) {
                    Text(
                        "No sign recorded yet. Placeholder, pending linguist sign-off.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                    )
                }
                state.signs.forEach { SignCard(it) }
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        color = TextPrimary,
        modifier = Modifier.semantics { heading() },
    )
}

@Composable
private fun SenseCard(sense: Sense) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(SurfaceInset)
                .semantics(mergeDescendants = true) { contentDescription = senseSummary(sense) }
                .padding(10.dp),
    ) {
        Text(
            text = "${sense.senseNo}. ${sense.gloss}",
            style = MaterialTheme.typography.bodyLarge,
            color = TextPrimary,
        )
        val decomposition =
            if (sense.primes.isEmpty()) {
                formStatusLabel(sense.decompStatus)
            } else {
                "${sense.primes.joinToString(" ")}  ·  ${formStatusLabel(sense.decompStatus)}"
            }
        Text(
            text = "primes: $decomposition",
            style = MaterialTheme.typography.labelSmall,
            fontFamily = FontFamily.Monospace,
            color = TextSecondary,
        )
    }
}

@Composable
private fun SignCard(sign: Sign) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(SurfaceInset)
                .semantics(mergeDescendants = true) { contentDescription = signSummary(sign) }
                .padding(10.dp),
    ) {
        val hamnosys = sign.hamnosys.ifBlank { "not set (placeholder)" }
        Text(
            text = "HamNoSys: $hamnosys",
            style = MaterialTheme.typography.bodyMedium,
            fontFamily = FontFamily.Monospace,
            color = TextPrimary,
        )
        Text(
            text = formStatusLabel(sign.formStatus),
            style = MaterialTheme.typography.labelSmall,
            color = TextSecondary,
        )
    }
}
