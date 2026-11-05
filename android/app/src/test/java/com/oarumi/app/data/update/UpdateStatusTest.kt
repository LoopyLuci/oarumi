package com.oarumi.app.data.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class UpdateStatusTest {
    private fun release(
        tag: String,
        apkName: String?,
    ): String {
        val assets =
            if (apkName == null) {
                "[]"
            } else {
                val url = "https://example.invalid/$apkName"
                val digest = "sha256:" + "ab".repeat(32)
                """[{"name":"$apkName","browser_download_url":"$url","size":10,"digest":"$digest"}]"""
            }
        return """{"tag_name":"$tag","html_url":"https://example.invalid/release","assets":$assets}"""
    }

    @Test
    fun `build suffixes are removed before comparing`() {
        assertEquals("0.1.0-alpha.4", installedVersion("0.1.0-alpha.4-debug"))
        assertEquals("0.1.0-alpha.3", installedVersion("0.1.0-alpha.3-phrasebook"))
        assertEquals("0.1.0-alpha.3", installedVersion("0.1.0-alpha.3-phrasebook-debug"))
    }

    @Test
    fun `an equal or older release is up to date`() {
        val status =
            decideUpdate(
                release("v0.1.0-alpha.3", "oarumi-mlkit-release-0.1.0-alpha.3.apk"),
                "0.1.0-alpha.3",
                "mlkit",
            )
        assertTrue(status is UpdateStatus.UpToDate)
    }

    @Test
    fun `a newer release offers the apk for this flavor`() {
        val status =
            decideUpdate(
                release("v0.1.0-alpha.4", "oarumi-mlkit-release-0.1.0-alpha.4.apk"),
                "0.1.0-alpha.3",
                "mlkit",
            )
        val available = status as UpdateStatus.Available
        assertEquals("oarumi-mlkit-release-0.1.0-alpha.4.apk", available.apk?.name)
        assertEquals("ab".repeat(32), available.apk?.sha256)
    }

    @Test
    fun `a newer release without an apk for this flavor is reported without one`() {
        val status = decideUpdate(release("v0.1.0-alpha.4", null), "0.1.0-alpha.3", "argos")
        val available = status as UpdateStatus.Available
        assertNull(available.apk)
    }
}
