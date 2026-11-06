package com.oarumi.app.di

import android.content.Context
import androidx.work.WorkManager
import com.oarumi.app.bootstrap.BootstrapStateStore
import com.oarumi.app.data.audio.AndroidAudioSource
import com.oarumi.app.data.avatar.CwasaController
import com.oarumi.app.data.db.AndroidLanguageStore
import com.oarumi.app.data.db.AppDatabase
import com.oarumi.app.data.tts.AndroidTtsBackend
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import oarumi.config.EngineConfig
import oarumi.db.LanguageStore
import oarumi.nsm.NSMDecomposerTierA
import oarumi.nsm.NSMRealizer
import oarumi.nsm.NSMValidator
import oarumi.pipeline.Pipeline
import oarumi.pivot.PivotTranslator
import oarumi.reliability.AuditLog
import oarumi.reliability.ReliabilityStack
import oarumi.reliability.StaticCapabilitySource
import oarumi.renderers.AudioAssetLibrary
import oarumi.renderers.AudioSource
import oarumi.renderers.SignRenderer
import oarumi.renderers.TactileRenderer
import oarumi.renderers.TtsBackend
import oarumi.renderers.TtsRenderer
import java.nio.file.Files
import javax.inject.Qualifier
import javax.inject.Singleton

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class OarumiHome

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton @OarumiHome
    fun provideHome(
        @ApplicationContext ctx: Context,
    ): java.nio.file.Path {
        // Paths.get, not Path.of: Path.of is not in the Android runtime before API 33.
        val dir = java.nio.file.Paths.get(ctx.filesDir.absolutePath, "oarumi")
        Files.createDirectories(dir)
        return dir
    }

    @Provides @Singleton
    fun provideEngineConfig(
        @OarumiHome home: java.nio.file.Path,
    ): EngineConfig =
        EngineConfig(
            home = home,
            strictParity = false,
            devModels = false,
            offline = true,
            logLevel = "INFO",
        )

    @Provides @Singleton
    fun provideAppDatabase(
        @ApplicationContext ctx: Context,
    ): AppDatabase = AppDatabase.create(ctx)

    @Provides @Singleton
    fun provideLanguageStore(db: AppDatabase): LanguageStore = AndroidLanguageStore(db)

    @Provides @Singleton
    fun provideAudioSource(
        @ApplicationContext ctx: Context,
    ): AudioSource = AndroidAudioSource(ctx.assets)

    @Provides @Singleton
    fun provideAudioLibrary(source: AudioSource): AudioAssetLibrary = AudioAssetLibrary(source, requireVerified = false)

    @Provides @Singleton
    fun provideAndroidTtsBackend(
        @ApplicationContext ctx: Context,
    ): AndroidTtsBackend = AndroidTtsBackend(ctx)

    @Provides @Singleton
    fun provideTtsBackend(backend: AndroidTtsBackend): TtsBackend = backend

    @Provides @Singleton
    fun provideWorkManager(
        @ApplicationContext ctx: Context,
    ): WorkManager = WorkManager.getInstance(ctx)

    @Provides @Singleton
    fun provideBootstrapStateStore(): BootstrapStateStore = BootstrapStateStore()

    @Provides @Singleton
    fun provideCwasaController(): CwasaController = CwasaController()

    @Provides @Singleton
    fun provideAuditLog(
        @OarumiHome home: java.nio.file.Path,
    ): AuditLog = AuditLog(home.resolve("audit.jsonl"))

    @Provides @Singleton
    fun provideReliabilityStack(
        audit: AuditLog,
        store: LanguageStore,
    ): ReliabilityStack {
        // The canary root is intentionally empty in the app; canaries are a dev-time
        // concept. Real failover recovery uses the shield + FSM without canary
        // gating until a canary set ships with the app.
        val emptyRoot = java.nio.file.Files.createTempDirectory("oarumi-canary-")
        return ReliabilityStack.create(
            auditPath = audit.path,
            canaryRoot = emptyRoot,
            capabilities =
                StaticCapabilitySource(
                    db = store,
                    offline = true,
                ),
        )
    }

    @Provides @Singleton
    fun providePipeline(
        store: LanguageStore,
        config: EngineConfig,
        audio: AudioAssetLibrary,
        ttsBackend: TtsBackend,
    ): Pipeline {
        val pipeline =
            Pipeline(
                db = store,
                config = config,
                pivot = PivotTranslator(config),
                decomposer = NSMDecomposerTierA(store),
                realizer = NSMRealizer(store),
                validator = NSMValidator(store),
            )
        val tts = TtsRenderer(audio = audio, backend = ttsBackend)
        val sign = SignRenderer(useExternal = false)
        val tactile = TactileRenderer()
        pipeline.registerRenderer("spoken") { s -> tts.render(s).toJsonObject() }
        pipeline.registerRenderer("signed") { s -> sign.render(s).toJsonObject() }
        pipeline.registerRenderer("tactile") { s -> tactile.render(s).toJsonObject() }
        return pipeline
    }
}
