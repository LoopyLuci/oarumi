package com.oarumi.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.oarumi.app.bootstrap.BootstrapViewModel
import com.oarumi.app.bootstrap.BootstrapWizard
import com.oarumi.app.data.avatar.CwasaController
import com.oarumi.app.ui.OarumiRoot
import com.oarumi.app.ui.theme.OarumiTheme
import com.oarumi.app.ui.translate.TranslateViewModel
import dagger.hilt.android.AndroidEntryPoint
import oarumi.config.EngineConfig
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject lateinit var config: EngineConfig

    @Inject lateinit var cwasaController: CwasaController

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            OarumiTheme {
                val bootstrapViewModel: BootstrapViewModel = hiltViewModel()
                val bootstrapState by bootstrapViewModel.state.collectAsStateWithLifecycle()
                var allowMainUi by remember { mutableStateOf(false) }

                val ready = bootstrapState.ready
                val shouldShowWizard = !ready && !allowMainUi

                if (shouldShowWizard) {
                    BootstrapWizard(
                        onReady = { allowMainUi = true },
                        viewModel = bootstrapViewModel,
                    )
                } else {
                    val rootViewModel: TranslateViewModel = hiltViewModel()
                    val auditTailProvider = remember(rootViewModel) { { rootViewModel.auditTail() } }
                    OarumiRoot(
                        controller = cwasaController,
                        config = config,
                        auditTailProvider = auditTailProvider,
                    )
                }
            }
        }
    }

    @Suppress("unused")
    private fun touchModifier(): Modifier = Modifier.fillMaxSize()
}
