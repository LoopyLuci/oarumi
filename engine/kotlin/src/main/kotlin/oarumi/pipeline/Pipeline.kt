package oarumi.pipeline

import oarumi.config.EngineConfig
import oarumi.db.LanguageStore
import oarumi.errors.FallbackRequiredException
import oarumi.errors.ValidationException
import oarumi.nsm.NSMDecomposerTierA
import oarumi.nsm.NSMRealizer
import oarumi.nsm.NSMValidator
import oarumi.pivot.PivotTranslator
import oarumi.reliability.IntentRouter
import oarumi.reliability.StaticCapabilitySource
import oarumi.types.FailoverEvent
import oarumi.types.NsmStructure
import oarumi.types.OarumiSurface
import oarumi.types.PivotPayload
import oarumi.types.PivotResult
import oarumi.types.TraceEntry
import oarumi.types.TranslationRequest
import oarumi.types.TranslationResult
import java.time.Instant
import java.util.UUID

class Pipeline(
    private val db: LanguageStore,
    private val config: EngineConfig,
    private val pivot: PivotTranslator = PivotTranslator(config),
    private val decomposer: NSMDecomposerTierA = NSMDecomposerTierA(db),
    private val realizer: NSMRealizer = NSMRealizer(db),
    private val validator: NSMValidator = NSMValidator(db),
    private val router: IntentRouter =
        IntentRouter(
            StaticCapabilitySource(db = db, offline = config.offline),
        ),
) {
    private val renderers: MutableMap<String, (OarumiSurface) -> kotlinx.serialization.json.JsonObject> =
        mutableMapOf()

    fun registerRenderer(
        modality: String,
        fn: (OarumiSurface) -> kotlinx.serialization.json.JsonObject,
    ) {
        renderers[modality] = fn
    }

    fun translate(req: TranslationRequest): TranslationResult {
        val failover = mutableListOf<FailoverEvent>()

        // 0. Router: refuse early so downstream steps see a stable contract (mirrors Python).
        val route = router.route(req)
        if (route.kind == "refuse") {
            return TranslationResult(
                requestId = "",
                input = req.toPayload(),
                pivot = PivotPayload("", "en", "phrasebook"),
                nsm = NsmStructure.EMPTY,
                surface = OarumiSurface.empty(req.modality),
                modalities = emptyMap(),
                trace = listOf(TraceEntry("intent", "deterministic", route.reason)),
                failoverEvents = listOf(FailoverEvent("intent_router", route.reason, now())),
                degraded = true,
            )
        }

        // 1. Pivot
        val pivotResult: PivotResult =
            try {
                pivot.translate(req.text, req.lang, "en")
            } catch (e: FallbackRequiredException) {
                return degraded(req, emptyPivot(), failover + FailoverEvent(e.component, e.trigger, now()))
            }

        // 2. Decompose
        val nsm: NsmStructure =
            try {
                decomposer.decompose(pivotResult.text)
            } catch (e: ValidationException) {
                return degraded(req, pivotResult, failover + FailoverEvent("nsm_decompose", "validation", now()))
            }

        // 3. Validate (defense in depth)
        val outcome = validator.validate(nsm)
        val finalNsm =
            if (!outcome.valid) {
                failover += FailoverEvent("nsm_validate", "validation", now())
                nsm.copy(valid = false)
            } else {
                nsm
            }

        // 4. Realize
        val surface: OarumiSurface =
            try {
                realizer.realize(finalNsm, modality = req.modality)
            } catch (e: ValidationException) {
                return degraded(
                    req,
                    pivotResult,
                    failover + FailoverEvent("nsm_realize", "validation", now()),
                    finalNsm,
                )
            }

        val modalities = mutableMapOf<String, kotlinx.serialization.json.JsonObject>()
        val targets =
            buildList {
                add(req.modality)
                req.targetModality?.let { if (it != req.modality) add(it) }
            }
        for (m in targets) {
            val r = renderers[m] ?: continue
            try {
                modalities[m] = r(surface)
            } catch (e: Exception) {
                failover += FailoverEvent("render_$m", "unavailable", now())
            }
        }

        return TranslationResult(
            requestId = UUID.randomUUID().toString(),
            input = req.toPayload(),
            pivot = PivotPayload(pivotResult.text, pivotResult.lang, pivotResult.source),
            nsm = finalNsm,
            surface = surface,
            modalities = modalities,
            trace = pivotResult.trace,
            failoverEvents = failover,
            degraded = failover.isNotEmpty() || !finalNsm.valid,
        )
    }

    private fun emptyPivot() = PivotResult(text = "", lang = "en", source = "phrasebook")

    private fun degraded(
        req: TranslationRequest,
        pivot: PivotResult,
        events: List<FailoverEvent>,
        nsm: NsmStructure = NsmStructure.EMPTY,
    ): TranslationResult =
        TranslationResult(
            requestId = "",
            input = req.toPayload(),
            pivot = PivotPayload(pivot.text, pivot.lang, pivot.source),
            nsm = nsm,
            surface = OarumiSurface.empty(req.modality),
            modalities = emptyMap(),
            trace = pivot.trace,
            failoverEvents = events,
            degraded = true,
        )

    private fun now(): String = Instant.now().toString()
}
