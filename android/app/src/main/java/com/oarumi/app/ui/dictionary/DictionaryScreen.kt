package com.oarumi.app.ui.dictionary

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextPrimary
import com.oarumi.app.ui.theme.TextSecondary
import oarumi.db.Lexeme
import oarumi.db.Prime

/** Search, browse by root class, and open an entry. Entries open [DictionaryEntryScreen]. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DictionaryScreen(
    onOpenEntry: (Int) -> Unit,
    viewModel: DictionaryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedTextField(
            value = state.query,
            onValueChange = viewModel::onQueryChange,
            label = { Text("Search the dictionary") },
            placeholder = { Text("e.g. who, manu, interrogative") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )

        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(DictionaryFilter.entries) { filter ->
                FilterChip(
                    selected = state.filter == filter,
                    onClick = { viewModel.onFilterChange(filter) },
                    label = { Text(filterLabel(filter, state)) },
                )
            }
        }

        if (state.filter == DictionaryFilter.Primes) {
            PrimeList(state.visiblePrimes, hasQuery = state.query.isNotBlank())
        } else if (state.results.isEmpty()) {
            Text(
                text = if (state.query.isBlank()) "(no words in this class yet)" else "(no matches)",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
            )
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                items(state.results, key = { it.id }) { lx ->
                    LexemeRow(lx, onClick = { onOpenEntry(lx.id) })
                }
            }
        }
    }
}

private fun filterLabel(
    filter: DictionaryFilter,
    state: DictionaryUiState,
): String {
    val count =
        when (filter) {
            DictionaryFilter.All -> state.rootCounts.values.sum()
            DictionaryFilter.Primes -> state.primes.size
            else -> state.rootCounts[filter.rootClass] ?: 0
        }
    return "${filter.label} ($count)"
}

@Composable
private fun LexemeRow(
    lx: Lexeme,
    onClick: () -> Unit,
) {
    val click = if (lx.click != null) " [${lx.click}]" else ""
    val status = if (lx.formStatus == "signed_off") "" else "  ·  ${formStatusLabel(lx.formStatus)}"
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(6.dp))
                .background(SurfaceInset)
                .clickable(onClickLabel = "Open entry", role = Role.Button, onClick = onClick)
                .semantics(mergeDescendants = true) { contentDescription = lexemeSummary(lx) }
                .padding(10.dp),
    ) {
        Text(
            text = "${lx.phonForm}$click",
            style = MaterialTheme.typography.titleMedium,
            color = TextPrimary,
        )
        Text(
            text = "${lx.gloss}  ·  ${lx.rootClass}  ·  freq ${lx.frequency}$status",
            style = MaterialTheme.typography.labelSmall,
            fontFamily = FontFamily.Monospace,
            color = TextSecondary,
        )
    }
}

@Composable
private fun PrimeList(
    primes: List<Prime>,
    hasQuery: Boolean,
) {
    if (primes.isEmpty()) {
        Text(
            text = if (hasQuery) "(no primes match)" else "(no primes loaded)",
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary,
        )
        return
    }
    LazyColumn(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items(primes, key = { it.id }) { p ->
            Column(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(6.dp))
                        .background(SurfaceInset)
                        .semantics(mergeDescendants = true) { contentDescription = primeSummary(p) }
                        .padding(10.dp),
            ) {
                Text(
                    text = "${p.spokenForm}  —  ${p.gloss}",
                    style = MaterialTheme.typography.titleMedium,
                    color = TextPrimary,
                )
                Text(
                    text = "[prime: ${p.id}]  ·  spoken form ${formStatusLabel(p.formStatus)}",
                    style = MaterialTheme.typography.labelSmall,
                    fontFamily = FontFamily.Monospace,
                    color = TextSecondary,
                )
            }
        }
    }
}
