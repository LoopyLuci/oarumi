package com.oarumi.app.ui.learn

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary

@Composable
fun LearnScreen(viewModel: LearnViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val prime = state.current

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (prime == null) {
            Text("No primes loaded. Run ./scripts/bootstrap.sh.", color = TextMuted)
            return@Column
        }

        Text(
            text = prime.id,
            style = MaterialTheme.typography.displayLarge,
            color = TextPrimary,
        )
        Text(
            text = prime.gloss,
            style = MaterialTheme.typography.headlineSmall,
            color = TextSecondary,
        )
        Spacer(Modifier.padding(8.dp))
        Text(
            text =
                buildString {
                    appendLine("category: ${prime.category}")
                    appendLine("spoken form: ${prime.spokenForm}")
                    appendLine("signed form: ${prime.signedForm}")
                    appendLine("tactile form: ${prime.tactileForm}")
                    appendLine("combinators: ${prime.combinators.joinToString(", ")}")
                    appendLine("nsm version: ${prime.nsmVersion}")
                }.trimEnd(),
            style = MaterialTheme.typography.labelSmall,
            fontFamily = FontFamily.Monospace,
            color = TextMuted,
        )

        Spacer(Modifier.weight(1f))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Button(onClick = viewModel::previous) { Text("← Previous") }
            Text(
                text = "${state.index + 1} / ${state.primes.size}",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted,
            )
            Button(onClick = viewModel::next) { Text("Next →") }
        }
    }
}
