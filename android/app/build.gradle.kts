import java.util.Base64
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.kapt")
    id("com.google.dagger.hilt.android")
}

// --- Signing config, loaded from key.properties or ANDROID_KEYSTORE_B64 ---------
val keystoreProperties =
    Properties().apply {
        val file = rootProject.file("key.properties")
        if (file.exists()) {
            file.inputStream().use { load(it) }
        }
    }

fun decodeKeystoreFromEnv(): java.io.File? {
    val b64 = System.getenv("ANDROID_KEYSTORE_B64") ?: return null
    val target = layout.buildDirectory.file("release.keystore").get().asFile
    target.parentFile.mkdirs()
    target.writeBytes(Base64.getDecoder().decode(b64))
    return target
}

val hasSigning =
    keystoreProperties.getProperty("storeFile") != null ||
        System.getenv("ANDROID_KEYSTORE_B64") != null

android {
    namespace = "com.oarumi.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.oarumi.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 3
        versionName = "0.1.0-alpha.3"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (hasSigning) {
            create("release") {
                val decoded = decodeKeystoreFromEnv()
                storeFile = decoded ?: file(keystoreProperties.getProperty("storeFile"))
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                    ?: keystoreProperties.getProperty("storePassword")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                    ?: keystoreProperties.getProperty("keyAlias")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
                    ?: keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            if (hasSigning) signingConfig = signingConfigs.getByName("release")
        }
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
    }

    flavorDimensions += "pivot"
    productFlavors {
        /**
         * mlkit: full build with Google ML Kit on-device translation.
         *   - ~30 MB per language model downloaded on first run
         *   - 50+ languages supported
         *   - default and recommended
         */
        create("mlkit") {
            dimension = "pivot"
            isDefault = true
        }
        /**
         * argos: minimal build without ML Kit.
         *   - no per-language downloads (everything bundled)
         *   - phrasebook-only translation, seed languages only
         *   - ~30 MB smaller APK
         *   - the naming is historical; a true Argos-on-Android port is not
         *     yet viable, so this flavor ships the phrasebook path that
         *     HANDOVER § 3 lists as the fallback for "ML Kit unavailable"
         */
        create("argos") {
            dimension = "pivot"
            versionNameSuffix = "-phrasebook"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }

    packaging {
        resources.excludes +=
            setOf(
                "/META-INF/{AL2.0,LGPL2.1}",
                "/META-INF/LICENSE*",
                "META-INF/DEPENDENCIES",
            )
    }

    applicationVariants.all {
        outputs.all {
            val output = this as com.android.build.gradle.internal.api.BaseVariantOutputImpl
            output.outputFileName = "oarumi-$flavorName-${buildType.name}-$versionName.apk"
        }
    }
}

// --- Asset staging --------------------------------------------------------------
val repoRoot = rootProject.projectDir.parentFile

val stageLanguageDb by tasks.registering(Copy::class) {
    val sourceDb = repoRoot.resolve("language/oarumi.db")
    from(sourceDb)
    into(layout.buildDirectory.dir("generated/assets"))
    doFirst {
        require(sourceDb.exists()) {
            "language/oarumi.db missing; run ./scripts/bootstrap.sh from the repo root"
        }
    }
}

val stageAudioAssets by tasks.registering(Copy::class) {
    val sourceDir = repoRoot.resolve("assets/audio")
    from(sourceDir) { into("audio") }
    into(layout.buildDirectory.dir("generated/assets"))
    doFirst {
        require(sourceDir.resolve("manifest.json").exists()) {
            "assets/audio/manifest.json missing; run tools/generate_audio_assets.py"
        }
    }
}

android.sourceSets["main"].assets.srcDir(
    layout.buildDirectory.dir("generated/assets"),
)

tasks.named("preBuild").configure {
    dependsOn(stageLanguageDb, stageAudioAssets)
}

// --- Dependencies ---------------------------------------------------------------
dependencies {
    implementation(project(":engine"))

    val composeBom = platform("androidx.compose:compose-bom:2024.05.00")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-android-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    implementation("androidx.hilt:hilt-work:1.2.0")
    kapt("androidx.hilt:hilt-compiler:1.2.0")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    // ML Kit only in the mlkit flavor.
    add("mlkitImplementation", "com.google.mlkit:translate:17.0.2")

    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.24")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:1.9.24")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("androidx.test:core:1.5.0")
    testImplementation("androidx.test.ext:junit:1.1.5")
    testImplementation("androidx.room:room-testing:2.6.1")
    testImplementation("androidx.work:work-testing:2.9.0")
    testImplementation("org.robolectric:robolectric:4.12.2")
    // ParityWithJvmTest reads the same DB through the JVM LanguageDb.
    testImplementation("org.xerial:sqlite-jdbc:3.45.2.0")

    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test:runner:1.5.2")
    androidTestImplementation("androidx.test:rules:1.5.0")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("org.jetbrains.kotlin:kotlin-test:1.9.24")
    androidTestImplementation("org.jetbrains.kotlin:kotlin-test-junit:1.9.24")
    androidTestImplementation(composeBom)
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation(composeBom)
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
