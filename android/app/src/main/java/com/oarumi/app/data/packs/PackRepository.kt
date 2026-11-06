package com.oarumi.app.data.packs

import android.content.Context
import android.content.res.AssetManager
import com.oarumi.app.data.net.HttpFetch
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import oarumi.lang.LanguageDetector
import oarumi.lang.LanguagePack
import oarumi.lang.PackEntry
import oarumi.lang.SpellChecker
import oarumi.lang.parsePack
import oarumi.lang.parsePackIndex
import oarumi.lang.verifyPack
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/** Where the packs built into the APK come from. */
interface BundledPacks {
    fun exists(name: String): Boolean

    fun read(name: String): String
}

/** Packs inside the APK's assets/packs folder. */
class AssetBundledPacks(
    private val assets: AssetManager,
) : BundledPacks {
    override fun exists(name: String): Boolean = assets.list(DIR)?.contains(name) == true

    override fun read(name: String): String = assets.open("$DIR/$name").bufferedReader().use { it.readText() }

    private companion object {
        const val DIR = "packs"
    }
}

/** Packs from a folder on disk. Used by unit tests, which cannot read merged APK assets. */
class DirectoryBundledPacks(
    private val dir: File,
) : BundledPacks {
    override fun exists(name: String): Boolean = File(dir, name).exists()

    override fun read(name: String): String = File(dir, name).readText()
}

/**
 * Language packs on this device. Base packs ship inside the APK. Extra packs
 * download from the repo once and are checked against the index before they
 * are kept. Mirrors desktop/packs.py.
 */
@Singleton
class PackRepository internal constructor(
    private val installedRoot: File,
    private val bundled: BundledPacks,
) {
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) : this(File(context.filesDir, "packs"), AssetBundledPacks(context.assets))

    /** Swappable for tests. The default fetches from GitHub. */
    internal var fetch: (String) -> ByteArray = { url -> HttpFetch.bytes(url) }

    private val indexEntries: List<PackEntry> by lazy { parsePackIndex(bundled.read(INDEX_FILE)) }

    private var detector: LanguageDetector? = null
    private val spellCheckers = mutableMapOf<String, SpellChecker>()

    fun entries(): List<PackEntry> = indexEntries

    fun isInstalled(entry: PackEntry): Boolean =
        File(installedRoot, entry.file).exists() || (entry.base && bundled.exists(entry.file))

    /** Downloads, verifies against the index, and keeps the pack. Throws if the check fails. */
    suspend fun download(entry: PackEntry) {
        withContext(Dispatchers.IO) {
            val blob = fetch(BASE_URL + entry.file)
            verifyPack(blob, entry)
            installedRoot.mkdirs()
            val partial = File(installedRoot, entry.file + ".partial")
            partial.writeBytes(blob)
            val target = File(installedRoot, entry.file)
            if (!partial.renameTo(target)) {
                partial.copyTo(target, overwrite = true)
                partial.delete()
            }
        }
        invalidate()
    }

    /** Removes the downloaded copy. A built-in base pack falls back to the APK copy. */
    fun remove(entry: PackEntry) {
        File(installedRoot, entry.file).delete()
        invalidate()
    }

    fun load(entry: PackEntry): LanguagePack {
        val downloaded = File(installedRoot, entry.file)
        val text = if (downloaded.exists()) downloaded.readText() else bundled.read(entry.file)
        return parsePack(text)
    }

    @Synchronized
    fun detector(): LanguageDetector {
        detector?.let { return it }
        val profiles = mutableMapOf<String, Map<String, Int>>()
        val dictionaries = mutableMapOf<String, Map<String, Int>>()
        for (entry in indexEntries) {
            if (!isInstalled(entry)) continue
            val pack = load(entry)
            profiles[entry.code] = pack.ngrams
            if (pack.words.isNotEmpty()) dictionaries[entry.code] = pack.words
        }
        return LanguageDetector(profiles, dictionaries).also { detector = it }
    }

    @Synchronized
    fun spellChecker(code: String): SpellChecker? {
        spellCheckers[code]?.let { return it }
        val entry = indexEntries.firstOrNull { it.code == code } ?: return null
        if (!entry.spell || !isInstalled(entry)) return null
        return SpellChecker(load(entry).words).also { spellCheckers[code] = it }
    }

    @Synchronized
    fun invalidate() {
        detector = null
        spellCheckers.clear()
    }

    private companion object {
        const val INDEX_FILE = "index.json"
        const val BASE_URL = "https://raw.githubusercontent.com/LoopyLuci/oarumi/main/language/packs/"
    }
}
