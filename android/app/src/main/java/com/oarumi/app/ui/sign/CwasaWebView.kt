package com.oarumi.app.ui.sign

import android.annotation.SuppressLint
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.oarumi.app.data.avatar.CwasaController

/**
 * Compose wrapper around the CWASA WebView. Buffers the last SiGML until the
 * page finishes loading, then plays it. Uses AndroidView because CWASA needs
 * the raw WebView (evaluateJavascript + file:// asset loading).
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun CwasaWebView(
    sigml: String?,
    controller: CwasaController,
    modifier: Modifier = Modifier,
) {
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var pageReady by remember { mutableStateOf(false) }

    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { context ->
            WebView(context).also { wv ->
                wv.webViewClient =
                    object : WebViewClient() {
                        override fun onPageFinished(
                            view: WebView?,
                            url: String?,
                        ) {
                            pageReady = true
                        }
                    }
                controller.attach(wv)
                webViewRef = wv
            }
        },
    )

    LaunchedEffect(pageReady, sigml, webViewRef) {
        val wv = webViewRef ?: return@LaunchedEffect
        if (!pageReady) return@LaunchedEffect
        if (sigml != null) controller.play(wv, sigml) else controller.clear(wv)
    }

    DisposableEffect(Unit) {
        onDispose {
            webViewRef?.destroy()
            webViewRef = null
        }
    }
}
