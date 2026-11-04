package com.oarumi.app.di

import com.oarumi.app.data.mlkit.MlKitTranslator
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Argos flavor: no ML Kit on the classpath. Provide a null stub so
 * BootstrapManager can still resolve its optional dependency.
 */
@Module
@InstallIn(SingletonComponent::class)
object MlKitModule {
    @Provides @Singleton
    fun provideMlKitTranslator(): MlKitTranslator? = null
}
