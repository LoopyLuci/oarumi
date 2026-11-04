package com.oarumi.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val OarumiColors =
    darkColorScheme(
        primary = AccentBlue,
        onPrimary = TextPrimary,
        secondary = AccentGreen,
        background = SurfaceDark,
        onBackground = TextPrimary,
        surface = SurfaceElevated,
        onSurface = TextPrimary,
        surfaceVariant = SurfaceRaised,
        onSurfaceVariant = TextSecondary,
        outline = BorderSubtle,
        outlineVariant = BorderStrong,
        error = BadgeWarnFg,
        onError = BadgeWarnBg,
    )

@Composable
fun OarumiTheme(
    @Suppress("UNUSED_PARAMETER") darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = OarumiColors,
        typography = OarumiTypography,
        content = content,
    )
}
