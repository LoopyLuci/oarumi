package com.oarumi.app.data.update

import com.oarumi.app.data.net.HttpStatusException
import kotlinx.coroutines.runBlocking
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class UpdateCheckerTest {
    private fun checkerAnswering(answer: () -> String): UpdateChecker = UpdateChecker().apply { fetch = { answer() } }

    private fun check(checker: UpdateChecker): UpdateStatus = runBlocking { checker.check("0.1.0-alpha.5", "argos") }

    @Test
    fun `a 404 for the latest release means none is published yet`() {
        val checker = checkerAnswering { throw HttpStatusException(404, UpdateChecker.RELEASES_LATEST_URL) }
        assertEquals(UpdateStatus.NoRelease, check(checker))
    }

    @Test
    fun `other server errors still fail so the worker retries`() {
        val checker = checkerAnswering { throw HttpStatusException(503, UpdateChecker.RELEASES_LATEST_URL) }
        assertFailsWith<HttpStatusException> { check(checker) }
    }

    @Test
    fun `a published release is compared with the installed version`() {
        val json = """{"tag_name":"v0.1.0-alpha.6","html_url":"https://example.invalid/release","assets":[]}"""
        assertTrue(check(checkerAnswering { json }) is UpdateStatus.Available)
    }
}
