package com.oarumi.app.di

import android.content.Context
import com.oarumi.app.data.mlkit.MlKitTranslator
import com.oarumi.app.data.mlkit.RealMlKitTranslator
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object MlKitModule {
    @Provides @Singleton
    fun provideMlKitTranslator(
        @ApplicationContext ctx: Context,
    ): MlKitTranslator = RealMlKitTranslator(ctx)
}
