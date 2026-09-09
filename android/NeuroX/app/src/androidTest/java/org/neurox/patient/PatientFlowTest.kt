package org.neurox.patient

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Setup UI tests use explicit state and never connect to a real patient server. */
@RunWith(AndroidJUnit4::class)
class PatientFlowTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test fun setupRequiresPatientCredentials() {
        composeTestRule.setContent {
            MaterialTheme { PatientSignInScreen(PatientAuthState(server = "https://care.example/")) { _, _, _ -> } }
        }
        composeTestRule.onNodeWithText("Welcome to NeuroX").assertIsDisplayed()
        composeTestRule.onNodeWithText("Sign in").assertIsNotEnabled()
        composeTestRule.onNodeWithText("Patient email").performTextInput("patient@example.com")
        composeTestRule.onNodeWithText("Password").performTextInput("PatientPassword!123")
        composeTestRule.onNodeWithText("Sign in").assertIsEnabled()
    }

    @Test fun submitPassesDetailsAndClearsPassword() {
        var submitted: List<String>? = null
        composeTestRule.setContent {
            MaterialTheme {
                PatientSignInScreen(PatientAuthState(server = "https://care.example/")) { server, email, password ->
                    submitted = listOf(server, email, password)
                }
            }
        }
        composeTestRule.onNodeWithText("Patient email").performTextInput("patient@example.com")
        composeTestRule.onNodeWithText("Password").performTextInput("PatientPassword!123")
        composeTestRule.onNodeWithText("Sign in").performClick()
        assertEquals(listOf("https://care.example/", "patient@example.com", "PatientPassword!123"), submitted)
        composeTestRule.onNodeWithText("Sign in").assertIsNotEnabled()
    }

    @Test fun setupShowsRecoverableErrors() {
        composeTestRule.setContent {
            MaterialTheme {
                PatientSignInScreen(PatientAuthState(error = "Check your connection and try again.")) { _, _, _ -> }
            }
        }
        composeTestRule.onNodeWithText("Check your connection and try again.").assertIsDisplayed()
    }

    @Test fun profileUsesTheSignedInPatient() {
        composeTestRule.setContent {
            MaterialTheme { Profile(Modifier, "Test Patient", 68, languageConfigFor("en-IN")) }
        }
        composeTestRule.onNodeWithText("Test Patient").assertIsDisplayed()
        composeTestRule.onNodeWithText("68 years", substring = true).assertExists()
        composeTestRule.onNodeWithText("Maya Devi").assertDoesNotExist()
        composeTestRule.onNodeWithText("Anita Devi").assertDoesNotExist()
    }

    @Test fun missingSafetyDataDoesNotClaimSafetyOrInventReturnTime() {
        composeTestRule.setContent {
            MaterialTheme { Safety(Modifier, null, {}, {}) }
        }
        composeTestRule.onNodeWithText("Safety status unavailable").assertIsDisplayed()
        composeTestRule.onNodeWithText("Not set").assertIsDisplayed()
        composeTestRule.onNodeWithText("6:00 PM").assertDoesNotExist()
        composeTestRule.onNodeWithText("At Home · Safe").assertDoesNotExist()
    }
}
