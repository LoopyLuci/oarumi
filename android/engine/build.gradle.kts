plugins {
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.plugin.serialization")
}

kotlin {
    jvmToolchain(17)
    // The engine source lives in engine/kotlin, shared with the desktop-side tooling.
    sourceSets {
        main { kotlin.srcDir("../../engine/kotlin/src/main/kotlin") }
        test { kotlin.srcDir("../../engine/kotlin/src/test/kotlin") }
    }
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.12.0")
    implementation("org.yaml:snakeyaml:2.2")

    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.24")
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    // LanguageDb (JVM) opens the DB through this driver. The app reads it through Room,
    // so the driver stays out of the APK.
    testImplementation("org.xerial:sqlite-jdbc:3.45.2.0")
}

tasks.test {
    useJUnitPlatform()
    // Frozen gold and fixtures are test inputs: re-run the suite when they change.
    inputs.dir(rootProject.file("../tests/parity/data"))
    inputs.dir(rootProject.file("../assets/audio"))
    // Parity tests read from the shared corpus at the repo root.
    systemProperty("oarumi.parity.data", rootProject.file("../tests/parity/data").absolutePath)
    systemProperty("oarumi.db", rootProject.file("../language/oarumi.db").absolutePath)
    systemProperty(
        "oarumi.parity.report",
        rootProject.layout.buildDirectory.file("parity-report.json").get().asFile.absolutePath,
    )
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    kotlinOptions.jvmTarget = "17"
}
