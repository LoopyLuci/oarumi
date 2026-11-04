package com.oarumi.app.ui.sign

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.data.avatar.CwasaController
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary

@Composable
fun SignScreen(
    controller: CwasaController,
    latestSigml: String?,
    viewModel: SignViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // Sync the shared "last sigml" from the translate screen into the VM.
    androidx.compose.runtime.LaunchedEffect(latestSigml) {
        if (latestSigml != null) {
            viewModel.updateFromSigml(latestSigml)
        }
    }

    Column(
        modifier =
            Modifier
                .fillMaxSize()
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = state.hint,
            style = androidx.compose.material3.MaterialTheme.typography.bodySmall,
            color = TextMuted,
        )

        Box(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .clip(RoundedCornerShape(6.dp))
                    .background(SurfaceInset),
        ) {
            CwasaWebView(
                sigml = state.sigml,
                controller = controller,
            )
        }

        state.sigml?.let { sigml ->
            Column(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .height(160.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(SurfaceInset)
                        .padding(8.dp)
                        .verticalScroll(rememberScrollState()),
            ) {
                Text(
                    text = sigml,
                    style = androidx.compose.material3.MaterialTheme.typography.labelSmall,
                    fontFamily = FontFamily.Monospace,
                    color = TextPrimary,
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Start,
        ) {
            Button(
                onClick = { viewModel.replay() },
                enabled = state.canPlay,
            ) {
                Text("Play sign")
            }
        }
    }
}
