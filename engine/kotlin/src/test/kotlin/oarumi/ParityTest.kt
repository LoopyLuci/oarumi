package oarumi

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.addJsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import oarumi.config.EngineConfig
import oarumi.db.LanguageDb
import oarumi.pipeline.Pipeline
import oarumi.renderers.AudioAssetLibrary
import oarumi.renderers.FileSystemAudioSource
import oarumi.renderers.SignRenderer
import oarumi.renderers.TactileRenderer
import oarumi.renderers.TtsRenderer
import oarumi.types.OarumiJson
import oarumi.types.TranslationRequest
import oarumi.types.TranslationResult
import org.junit.jupiter.api.Assumptions.assumeTrue
import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.extension
import kotlin.io.path.readText
import kotlin.test.Test
import kotlin.test.assertTrue

class ParityTest {
    private val corpusDir: Path =
        Path.of(System.getProperty("oarumi.parity.data") ?: "../tests/parity/data")
            .resolve("parity-basic")

    private val dbPath: Path =
        Path.of(System.getProperty("oarumi.db") ?: "../language/oarumi.db")

    /** Mirrors tools/parity_setup.py build_pipeline: same renderers, same deterministic backends. */
    private fun buildParityPipeline(
        db: LanguageDb,
        config: EngineConfig,
    ): Pipeline {
        val pipeline = Pipeline(db = db, config = config)
        val audioDir = config.home.resolve("assets").resolve("audio")
        assumeTrue(Files.exists(audioDir.resolve("manifest.json")), "audio manifest missing under $audioDir")
        val tts = TtsRenderer(audio = AudioAssetLibrary(FileSystemAudioSource(audioDir)), backend = null)
        val sign = SignRenderer(useExternal = false)
        val tactile = TactileRenderer()
        pipeline.registerRenderer("spoken") { s -> tts.render(s).toJsonObject() }
        pipeline.registerRenderer("signed") { s -> sign.render(s).toJsonObject() }
        pipeline.registerRenderer("tactile") { s -> tactile.render(s).toJsonObject() }
        return pipeline
    }

    @Test
    fun `kotlin engine matches python gold`() {
        assumeTrue(Files.exists(corpusDir), "corpus dir missing: $corpusDir")
        assumeTrue(Files.exists(dbPath), "language DB missing: $dbPath (run ./scripts/bootstrap.sh)")

        val cases =
            Files.list(corpusDir)
                .filter { it.extension == "json" }
                .sorted()
                .toList()
        assumeTrue(cases.isNotEmpty(), "corpus empty — Batch 13 populates it")

        val config =
            EngineConfig(
                home = dbPath.parent.parent.toAbsolutePath(),
                strictParity = true,
                devModels = true,
                offline = true,
                logLevel = "INFO",
            )

        LanguageDb(dbPath).use { db ->
            val pipeline = buildParityPipeline(db, config)
            var compared = 0
            var passed = 0
            val failures = mutableListOf<String>()
            val caseResults = mutableListOf<CaseResult>()

            for (casePath in cases) {
                val caseObj = Json.parseToJsonElement(casePath.readText()).jsonObject
                val requestObj = caseObj["request"]?.jsonObject ?: continue
                val req =
                    TranslationRequest(
                        text = requestObj["text"]!!.jsonPrimitive.content,
                        lang = requestObj["lang"]!!.jsonPrimitive.content,
                        modality = requestObj["modality"]?.jsonPrimitive?.content ?: "spoken",
                        targetModality = requestObj["target_modality"]?.jsonPrimitive?.content,
                    )

                val got: TranslationResult = pipeline.translate(req)
                val gotJson =
                    OarumiJson.encodeToJsonElement(
                        TranslationResult.serializer(),
                        got,
                    )

                val expected = caseObj["expected"]
                if (expected == null) continue

                compared += 1
                val match =
                    JsonCanonicalizer.canonical(gotJson) ==
                        JsonCanonicalizer.canonical(expected)
                caseResults +=
                    CaseResult(
                        caseId = casePath.fileName.toString().removeSuffix(".json"),
                        match = match,
                        got = gotJson,
                        expected = expected,
                    )
                if (match) {
                    passed += 1
                } else {
                    failures += "case=${casePath.fileName}: got=$gotJson expected=$expected"
                }
            }

            // Written before the assertions so the parity web GUI can show failing runs too.
            writeReport(corpusName = corpusDir.fileName.toString(), cases = caseResults)

            if (compared == 0) return // nothing to compare; passes with note

            assertTrue(
                failures.isEmpty(),
                "parity failures ($passed/$compared passed):\n" + failures.joinToString("\n"),
            )
            assertTrue(passed == compared)
        }
    }

    private fun writeReport(
        corpusName: String,
        cases: List<CaseResult>,
    ) {
        val pathStr = System.getProperty("oarumi.parity.report")
        val path =
            if (pathStr != null) {
                Path.of(pathStr)
            } else {
                Path.of("../build/parity-report.json").toAbsolutePath()
            }
        Files.createDirectories(path.parent)
        val json =
            buildJsonObject {
                put("corpus", corpusName)
                put("target", "kotlin")
                put("total", cases.size)
                put("passed", cases.count { it.match })
                put("failed", cases.count { !it.match })
                putJsonArray("cases") {
                    cases.forEach { c ->
                        addJsonObject {
                            put("case_id", c.caseId)
                            put("match", c.match)
                            c.got?.let { put("got", it) }
                            c.expected?.let { put("expected", it) }
                            c.error?.let { put("error", it) }
                        }
                    }
                }
            }
        Files.writeString(path, json.toString())
    }

    /** Per-case outcome of the parity loop, serialised into the JSON report. */
    data class CaseResult(
        val caseId: String,
        val match: Boolean,
        val got: JsonElement? = null,
        val expected: JsonElement? = null,
        val error: String? = null,
    )

    @Test
    fun `deterministic path produces identical request for identical input`() {
        assumeTrue(Files.exists(dbPath), "language DB missing")
        val config =
            EngineConfig(
                home = dbPath.parent.parent.toAbsolutePath(),
                strictParity = true,
                devModels = true,
                offline = true,
                logLevel = "INFO",
            )
        LanguageDb(dbPath).use { db ->
            val pipeline = Pipeline(db = db, config = config)
            val req = TranslationRequest(text = "hola", lang = "es", modality = "spoken")
            val a = pipeline.translate(req)
            val b = pipeline.translate(req)
            // request_id and failover timestamps differ; everything else must match.
            assertTrue(
                JsonCanonicalizer.canonical(
                    OarumiJson.encodeToJsonElement(TranslationResult.serializer(), a),
                ) ==
                    JsonCanonicalizer.canonical(
                        OarumiJson.encodeToJsonElement(TranslationResult.serializer(), b),
                    ),
            )
        }
    }
}
