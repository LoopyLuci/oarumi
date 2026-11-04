package oarumi.config

import java.nio.file.Path

data class EngineConfig(
    val home: Path,
    val strictParity: Boolean,
    val devModels: Boolean,
    val offline: Boolean,
    val logLevel: String,
) {
    val dbPath: Path get() = home.resolve("language").resolve("oarumi.db")

    companion object {
        fun fromEnv(): EngineConfig {
            val home = Path.of(System.getenv("OARUMI_HOME") ?: ".").toAbsolutePath().normalize()
            return EngineConfig(
                home = home,
                strictParity = System.getenv("OARUMI_STRICT_PARITY") == "1",
                devModels = System.getenv("OARUMI_DEV_MODELS") != "0",
                offline = System.getenv("OARUMI_OFFLINE") == "1",
                logLevel = System.getenv("OARUMI_LOG_LEVEL") ?: "INFO",
            )
        }
    }
}
