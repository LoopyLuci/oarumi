package com.oarumi.app.data.packs

import kotlinx.coroutines.runBlocking
import oarumi.lang.PackEntry
import oarumi.lang.PackException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File
import java.nio.file.Files

@RunWith(RobolectricTestRunner::class)
class PackRepositoryTest {
    private lateinit var repo: PackRepository

    @Before
    fun setUp() {
        val installed = Files.createTempDirectory("packs-test").toFile()
        repo = PackRepository(installed, DirectoryBundledPacks(File("../../language/packs")))
    }

    private fun extra(code: String): PackEntry = repo.entries().first { it.code == code }

    /** The real pack file from the repo, so checksums match the shipped index. */
    private fun repoPack(file: String): ByteArray = File("../../language/packs/$file").readBytes()

    @Test
    fun `base packs are built in and extra packs are not`() {
        val base = repo.entries().filter { it.base }.map { it.code }.toSet()
        assertEquals(setOf("en", "es", "fr", "de", "zh", "ar"), base)
        assertTrue(repo.isInstalled(extra("es")))
        assertFalse(repo.isInstalled(extra("pt")))
    }

    @Test
    fun `base packs load from the apk and feed the detector and speller`() {
        assertNotNull(repo.spellChecker("es"))
        assertTrue("es" in repo.detector().languages)
        assertEquals(null, repo.spellChecker("pt"))
    }

    @Test
    fun `a download that fails the checksum is refused and nothing is kept`() {
        repo.fetch = { byteArrayOf(1, 2, 3) }
        val pt = extra("pt")
        try {
            runBlocking { repo.download(pt) }
            fail("expected the checksum check to refuse the download")
        } catch (e: PackException) {
            assertTrue(e.message.orEmpty().contains("pt"))
        }
        assertFalse(repo.isInstalled(pt))
    }

    @Test
    fun `a verified download is installed, used for detection, and can be removed`() {
        val pt = extra("pt")
        repo.fetch = { repoPack("pt.json") }
        runBlocking { repo.download(pt) }

        assertTrue(repo.isInstalled(pt))
        assertTrue("pt" in repo.detector().languages)
        assertNotNull(repo.spellChecker("pt"))

        repo.remove(pt)
        assertFalse(repo.isInstalled(pt))
        assertEquals(null, repo.spellChecker("pt"))
    }

    @Test
    fun `removing a built-in pack keeps the apk copy`() {
        val es = extra("es")
        repo.remove(es)
        assertTrue(repo.isInstalled(es))
    }
}
