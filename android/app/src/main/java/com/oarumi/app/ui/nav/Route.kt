package com.oarumi.app.ui.nav

import androidx.annotation.StringRes
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.ui.graphics.vector.ImageVector
import com.oarumi.app.R

enum class Route(
    val path: String,
    @StringRes val label: Int,
    val icon: ImageVector,
) {
    Translate("translate", R.string.nav_translate, Icons.Filled.Translate),
    Sign("sign", R.string.nav_sign, Icons.Filled.Visibility),
    Learn("learn", R.string.nav_learn, Icons.Filled.School),
    Dictionary("dictionary", R.string.nav_dictionary, Icons.Filled.Book),
    Settings("settings", R.string.nav_settings, Icons.Filled.Settings),
}

/**
 * Detail screen for one dictionary entry. It opens from the Dictionary screen, so it is not
 * a bottom-bar destination and stays out of [Route].
 */
object DictionaryEntryRoute {
    const val ARG = "lexemeId"
    const val PATTERN = "dictionary/entry/{$ARG}"

    fun path(lexemeId: Int): String = "dictionary/entry/$lexemeId"
}
