package com.oarumi.app.data.avatar

import android.webkit.WebView
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json

/**
 * Manages a WebView hosting the CWASA SiGML viewer.
 *
 * The asset HTML at assets/avatar/index.html defines window.playSigML(xml).
 * This class is the type-safe bridge; the WebView is created and owned by
 * the Compose layer (Batch 11).
 */
class CwasaController {
    private val json = Json { prettyPrint = false }

    fun attach(webView: WebView) {
        webView.settings.apply {
            javaScriptEnabled = true
            allowFileAccess = true
            allowContentAccess = false
            domStorageEnabled = false // not needed; keeps sandbox tight
        }
        webView.loadUrl("file:///android_asset/avatar/index.html")
    }

    /**
     * Injects the SiGML into the page. The page must have finished loading
     * (onPageFinished fires first). Callers should queue if necessary; the
     * Compose layer in Batch 11 does this with a LaunchedEffect.
     */
    fun play(
        webView: WebView,
        sigml: String,
    ) {
        val payload = json.encodeToString(String.serializer(), sigml)
        webView.evaluateJavascript("window.playSigML($payload);", null)
    }

    fun clear(webView: WebView) {
        webView.evaluateJavascript("window.playSigML('');", null)
    }
}
