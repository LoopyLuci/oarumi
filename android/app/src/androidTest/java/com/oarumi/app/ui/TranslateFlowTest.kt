package com.oarumi.app.ui

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.oarumi.app.MainActivity
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TranslateFlowTest {
    @get:Rule
    val rule = createAndroidComposeRule<MainActivity>()

    @Test
    fun translate_hola_shows_output() {
        rule.waitForIdle()
        rule.onNodeWithText("Input").performTextInput("hola")
        rule.onNodeWithText("Translate to Oarumi").performClick()
        rule.waitUntil(timeoutMillis = 5_000) {
            rule.onAllNodes(androidx.compose.ui.test.hasText("Surface:", substring = true))
                .fetchSemanticsNodes().isNotEmpty()
        }
        rule.onNodeWithText("Surface:", substring = true).assertExists()
    }

    @Test
    fun nav_to_sign_screen() {
        rule.waitForIdle()
        rule.onNodeWithText("Sign").performClick()
        rule.onNodeWithText("Run a translation with target modality = signed.").assertExists()
    }

    @Test
    fun nav_to_learn_screen() {
        rule.waitForIdle()
        rule.onNodeWithText("Learn").performClick()
        rule.onNodeWithText("← Previous").assertExists()
        rule.onNodeWithText("Next →").assertExists()
    }

    @Test
    fun nav_to_dictionary() {
        rule.waitForIdle()
        rule.onNodeWithText("Dictionary").performClick()
        rule.onNodeWithText("Search lexemes").assertExists()
    }
}
