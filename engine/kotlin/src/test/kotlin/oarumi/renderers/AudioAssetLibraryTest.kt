package oarumi.renderers

import oarumi.errors.IntegrityException
import org.junit.jupiter.api.Assumptions.assumeTrue
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class AudioAssetLibraryTest {
    private val assetDir: Path =
        Path.of(System.getProperty("user.dir")).resolve("../../assets/audio").normalize()

    @Test
    fun `manifest_has_19_assets`() {
        assumeTrue(
            Files.exists(assetDir.resolve("manifest.json")),
            "run tools/generate_audio_assets.py first",
        )
        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        assertEquals(19, lib.ids().size)
    }

    @Test
    fun `all_hashes_verify_when_present`() {
        assumeTrue(Files.exists(assetDir.resolve("manifest.json")))
        // Only run when hashes are populated; otherwise skip (dev mode).
        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        val hasHashes = lib.ids().all { lib.get(it).sha256.isNotEmpty() }
        assumeTrue(hasHashes, "manifest has empty hashes; run tools/generate_audio_assets.py")
        // Re-instantiate with verification on — must not throw.
        AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = true)
    }

    @Test
    fun `corrupted_asset_raises`() {
        assumeTrue(Files.exists(assetDir.resolve("manifest.json")))
        val lib = AudioAssetLibrary(FileSystemAudioSource(assetDir), requireVerified = false)
        val anyAsset = lib.get(lib.ids().first())
        assumeTrue(anyAsset.sha256.isNotEmpty(), "manifest has empty hashes")

        // Copy the bundle to a temp dir, corrupt one file, verify rejection.
        val tmp = Files.createTempDirectory("audio-corrupt-")
        Files.copy(assetDir.resolve("manifest.json"), tmp.resolve("manifest.json"))
        for (id in lib.ids()) {
            val asset = lib.get(id)
            val target = tmp.resolve(asset.relPath)
            target.parent?.let { Files.createDirectories(it) }
            Files.copy(assetDir.resolve(asset.relPath), target)
        }
        Files.write(tmp.resolve(anyAsset.relPath), "corrupted".toByteArray())

        assertFailsWith<IntegrityException> {
            AudioAssetLibrary(FileSystemAudioSource(tmp), requireVerified = true)
        }
    }

    @Test
    fun `missing_manifest_raises`() {
        val tmp = Files.createTempDirectory("audio-empty-")
        assertFailsWith<java.io.FileNotFoundException> {
            AudioAssetLibrary(FileSystemAudioSource(tmp))
        }
    }
}
