package com.oarumi.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.oarumi.app.data.avatar.CwasaController
import com.oarumi.app.ui.common.OarumiStatusBar
import com.oarumi.app.ui.dictionary.DictionaryScreen
import com.oarumi.app.ui.learn.LearnScreen
import com.oarumi.app.ui.nav.Route
import com.oarumi.app.ui.sign.SignScreen
import com.oarumi.app.ui.theme.SurfaceDark
import com.oarumi.app.ui.translate.TranslateScreen
import oarumi.config.EngineConfig
import oarumi.types.TranslationResult

@Composable
fun OarumiRoot(
    controller: CwasaController,
    config: EngineConfig,
    auditTailProvider: () -> String,
) {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val currentDest = backStack?.destination

    var latestResult by remember { mutableStateOf<TranslationResult?>(null) }
    var auditTail by remember { mutableStateOf("(loading…)") }

    LaunchedEffect(latestResult) {
        auditTail = auditTailProvider()
    }

    Scaffold(
        containerColor = SurfaceDark,
        bottomBar = {
            NavigationBar {
                Route.entries.forEach { route ->
                    val selected = currentDest?.hierarchy?.any { it.route == route.path } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(route.path) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(route.icon, contentDescription = null) },
                        label = { Text(stringResource(route.label)) },
                    )
                }
            }
        },
    ) { padding ->
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .background(SurfaceDark)
                    .padding(padding),
        ) {
            NavHost(
                navController = navController,
                startDestination = Route.Translate.path,
                modifier = Modifier.weight(1f),
            ) {
                composable(Route.Translate.path) {
                    TranslateScreen(
                        onResultReady = { result ->
                            latestResult = result
                            auditTail = auditTailProvider()
                        },
                    )
                }
                composable(Route.Sign.path) {
                    SignScreen(
                        controller = controller,
                        latestSigml =
                            (
                                latestResult?.modalities?.get("signed")
                                    ?.get("sigml") as? kotlinx.serialization.json.JsonPrimitive
                            )?.content,
                    )
                }
                composable(Route.Learn.path) {
                    LearnScreen()
                }
                composable(Route.Dictionary.path) {
                    DictionaryScreen()
                }
            }

            OarumiStatusBar(
                offline = config.offline,
                degraded = latestResult?.degraded == true,
                auditTail = auditTail,
                onRefreshAudit = { auditTail = auditTailProvider() },
            )
        }
    }
}
