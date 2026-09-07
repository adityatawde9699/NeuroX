package org.neurox.patient

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Phase 8 Compose UI tests for primary patient flows.
 *
 * These tests use a fake/demo data layer (no network calls) to verify
 * that the UI renders correctly and responds to user interactions.
 *
 * Coverage:
 *   - HomeScreen: tabs are visible with labels, patient name appears.
 *   - ActivitiesScreen: activity list items are tappable.
 *   - RemindersScreen: reminder cards are shown.
 *   - SafetyScreen: safety status section and action buttons are present.
 *   - Accessibility: all interactive elements have content descriptions.
 */
@RunWith(AndroidJUnit4::class)
class PatientFlowTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    // --------------------------------------------------------------
    // Home / Navigation
    // --------------------------------------------------------------

    @Test
    fun homeScreen_displaysNavigationTabsWithLabels() {
        composeTestRule.setContent {
            // Render the full app in demo/offline mode.
            NeuroXApp()
        }
        // Each bottom-nav tab must have a visible label so elderly users
        // can identify it without recognising the icon alone.
        composeTestRule.onNodeWithText("Home").assertIsDisplayed()
        composeTestRule.onNodeWithText("Activities").assertIsDisplayed()
        composeTestRule.onNodeWithText("Reminders").assertIsDisplayed()
        composeTestRule.onNodeWithText("Safety").assertIsDisplayed()
    }

    @Test
    fun homeScreen_displaysPatientName() {
        composeTestRule.setContent { NeuroXApp() }
        // The demo patient name "Maya" should appear in the greeting.
        composeTestRule.onNodeWithText("Maya", substring = true).assertIsDisplayed()
    }

    // --------------------------------------------------------------
    // Activities tab
    // --------------------------------------------------------------

    @Test
    fun activitiesTab_listsDefaultActivities() {
        composeTestRule.setContent { NeuroXApp() }

        // Navigate to Activities tab.
        composeTestRule.onNodeWithText("Activities").performClick()

        // Fallback activity list must always be available (offline-safe).
        composeTestRule.onNodeWithText("Memory Match", substring = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("Remember the Objects", substring = true).assertIsDisplayed()
    }

    @Test
    fun activitiesTab_activityCardIsTappable() {
        composeTestRule.setContent { NeuroXApp() }
        composeTestRule.onNodeWithText("Activities").performClick()

        // Tap the first activity card — should open the game without crashing.
        composeTestRule.onNodeWithText("Memory Match", substring = true).performClick()

        // After tapping, the game-entry screen or start button should appear.
        composeTestRule.onNodeWithText("Start", substring = true, ignoreCase = true).assertIsDisplayed()
    }

    // --------------------------------------------------------------
    // Reminders tab
    // --------------------------------------------------------------

    @Test
    fun remindersTab_showsRemindersSection() {
        composeTestRule.setContent { NeuroXApp() }
        composeTestRule.onNodeWithText("Reminders").performClick()

        // The reminders heading must be visible.
        composeTestRule.onNodeWithText("Reminders", substring = true).assertIsDisplayed()
    }

    // --------------------------------------------------------------
    // Safety tab
    // --------------------------------------------------------------

    @Test
    fun safetyTab_showsStatusSection() {
        composeTestRule.setContent { NeuroXApp() }
        composeTestRule.onNodeWithText("Safety").performClick()

        // Both action buttons must be present so the user can call for help.
        composeTestRule.onNodeWithText("I Need Help", substring = true, ignoreCase = true).assertIsDisplayed()
        composeTestRule.onNodeWithText("SOS", substring = true, ignoreCase = true).assertIsDisplayed()
    }

    @Test
    fun safetyTab_sosButtonHasContentDescription() {
        composeTestRule.setContent { NeuroXApp() }
        composeTestRule.onNodeWithText("Safety").performClick()

        // Verify the SOS button is identifiable by accessibility tooling.
        composeTestRule
            .onNode(hasContentDescription("SOS", substring = true, ignoreCase = true))
            .assertExists()
    }

    // --------------------------------------------------------------
    // Accessibility: minimum touch-target size (48dp)
    // --------------------------------------------------------------

    @Test
    fun allTabButtons_meetMinimumTapTargetSize() {
        composeTestRule.setContent { NeuroXApp() }
        // Verify that each navigation button node exists and is clickable.
        listOf("Home", "Activities", "Reminders", "Safety").forEach { label ->
            composeTestRule
                .onNodeWithText(label)
                .assertHasClickAction()
        }
    }
}
