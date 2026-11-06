package oarumi.updates

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class UpdatesTest {
    @Test
    fun `orders semver versions the same way as the python engine`() {
        val ordered =
            listOf(
                "0.1.0-alpha.3",
                "0.1.0-alpha.4",
                "0.1.0-alpha.9",
                "0.1.0-alpha.10",
                "0.1.0-beta.1",
                "0.1.0",
                "0.2.0",
            )
        for (index in 0 until ordered.size - 1) {
            assertTrue(isNewer(ordered[index + 1], ordered[index]), "${ordered[index + 1]} > ${ordered[index]}")
            assertFalse(isNewer(ordered[index], ordered[index + 1]))
        }
        assertFalse(isNewer("v0.1.0-alpha.4", "0.1.0-alpha.4"))
    }

    @Test
    fun `alpha without a number sorts before alpha dot one`() {
        assertTrue(isNewer("1.0.0-alpha.1", "1.0.0-alpha"))
        assertTrue(isNewer("1.0.0-alpha.beta", "1.0.0-alpha.1"))
    }

    @Test
    fun `picks the apk for the running flavor and reads checksums`() {
        val json =
            """
            {"tag_name":"v0.1.0-alpha.4","html_url":"https://example.invalid/r",
             "assets":[
               {"name":"oarumi-argos-release-0.1.0-alpha.4-phrasebook.apk","browser_download_url":"https://example.invalid/a","size":10,"digest":"sha256:${"ab".repeat(
                32,
            )}"},
               {"name":"oarumi-mlkit-release-0.1.0-alpha.4.apk","browser_download_url":"https://example.invalid/m","size":12,"digest":"sha256:${"cd".repeat(
                32,
            )}"},
               {"name":"SHA256SUMS","browser_download_url":"https://example.invalid/s","size":1}
             ]}
            """.trimIndent()
        val release = parseRelease(json)
        val asset = pickApk(release, "mlkit")
        assertEquals("oarumi-mlkit-release-0.1.0-alpha.4.apk", asset?.name)
        assertEquals("cd".repeat(32), asset?.sha256)
        assertNull(pickApk(release, "unknown"))
    }
}
