package com.oarumi.app.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        PrimeEntity::class,
        LexemeEntity::class,
        SenseEntity::class,
        SignEntity::class,
        TactileEntity::class,
        GoldEntity::class,
        MigrationEntity::class,
    ],
    version = 2,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun primeDao(): PrimeDao

    abstract fun lexemeDao(): LexemeDao

    abstract fun senseDao(): SenseDao

    abstract fun signDao(): SignDao

    abstract fun tactileDao(): TactileDao

    abstract fun goldDao(): GoldDao

    companion object {
        const val DB_NAME = "oarumi.db"

        /**
         * Open the pre-seeded database from assets. createFromAsset copies the
         * file into databases/ on first run; subsequent runs reuse the copy.
         * The copy is never modified by the app.
         */
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, DB_NAME)
                .createFromAsset(DB_NAME)
                .fallbackToDestructiveMigration()
                .build()
    }
}
