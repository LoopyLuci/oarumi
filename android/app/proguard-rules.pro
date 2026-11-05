# kotlinx.serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class **$$serializer { *; }
-keepclasseswithmembers class ** {
    @kotlinx.serialization.Serializable <fields>;
}

# Engine public API
-keep class oarumi.types.** { *; }
-keep class oarumi.db.** { *; }
-keep class oarumi.renderers.** { *; }

# Room
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-dontwarn androidx.room.paging.**

# Hilt
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keep class * extends dagger.hilt.android.internal.managers.ViewComponentManager$FragmentContextWrapper

# ML Kit (per its consumer rules, but be explicit)
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**

# WorkManager
-keep class * extends androidx.work.Worker
-keep class * extends androidx.work.CoroutineWorker
-keep class androidx.work.impl.WorkManagerImpl { *; }
-dontwarn androidx.work.**

# Bootstrap manager / state
-keep class com.oarumi.app.bootstrap.** { *; }

# sqlite-jdbc and slf4j refer to classes that Android does not ship. Those code
# paths never run on a device, so R8 only needs to stop failing on them.
-dontwarn java.sql.JDBCType
-dontwarn org.slf4j.impl.StaticLoggerBinder
