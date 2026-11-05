package oarumi.lang

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Runs the same cases as tests/parity/lang/cases.json that the Python engine runs. */
class LanguageParityTest {
    private val packsDir: Path = Path.of(System.getProperty("oarumi.packs.dir"))
    private val casesFile: Path = Path.of(System.getProperty("oarumi.lang.cases"))

    private val packs: Map<String, LanguagePack> by lazy {
        val entries = parsePackIndex(Files.readString(packsDir.resolve("index.json")))
        entries.associate { entry ->
            val pack = parsePack(Files.readString(packsDir.resolve(entry.file)))
            entry.code to pack
        }
    }

    private val detector: LanguageDetector by lazy {
        LanguageDetector(
            profiles = packs.mapValues { it.value.ngrams },
            dictionaries = packs.filterValues { it.words.isNotEmpty() }.mapValues { it.value.words },
        )
    }

    private val cases by lazy { Json.parseToJsonElement(Files.readString(casesFile)).jsonObject }

    @Test
    fun `detection matches the shared cases`() {
        val failures = mutableListOf<String>()
        for (case in cases.getValue("detect").jsonArray) {
            val item = case.jsonObject
            val text = item.getValue("text").jsonPrimitive.content
            val expected = item.getValue("code").let { if (it is JsonNull) null else it.jsonPrimitive.content }
            val got = detector.detect(text).code
            if (got != expected) failures += "detect '$text': got $got expected $expected"
        }
        assertTrue(failures.isEmpty(), failures.joinToString("\n"))
    }

    @Test
    fun `suggestions match the shared cases`() {
        for (case in cases.getValue("suggest").jsonArray) {
            val item = case.jsonObject
            val lang = item.getValue("lang").jsonPrimitive.content
            val checker = SpellChecker(packs.getValue(lang).words)
            val word = item.getValue("word").jsonPrimitive.content
            assertEquals(item.getValue("first").jsonPrimitive.content, checker.suggest(word).first(), "suggest $word")
        }
    }

    @Test
    fun `spell check flags the shared unknown words`() {
        val case = cases.getValue("check").jsonArray.first().jsonObject
        val checker = SpellChecker(packs.getValue(case.getValue("lang").jsonPrimitive.content).words)
        val flagged = checker.check(case.getValue("text").jsonPrimitive.content).map { it.word }
        val expected = case.getValue("words").jsonArray.map { it.jsonPrimitive.content }
        assertEquals(expected, flagged)
    }

    @Test
    fun `pack index entries match their files`() {
        val entries = parsePackIndex(Files.readString(packsDir.resolve("index.json")))
        for (entry in entries) {
            verifyPack(Files.readAllBytes(packsDir.resolve(entry.file)), entry)
        }
    }
}
