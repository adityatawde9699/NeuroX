package org.neurox.patient

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceIntentParserTest {
    @Test
    fun helpTakesPriorityOverActivitiesAndReminders() {
        listOf(
            "help me with memory match",
            "start an activity emergency",
            "SOS open pattern",
            "show reminders I need assistance"
        ).forEach { phrase ->
            assertEquals(phrase, VoiceIntent.RequestHelp, IntentParser.parse(phrase))
        }
    }

    @Test
    fun familiarActivitiesRemainAvailable() {
        assertEquals(VoiceIntent.StartActivity("memory-match"), IntentParser.parse("play memory match"))
        assertEquals(VoiceIntent.ListReminders, IntentParser.parse("show reminders"))
        assertTrue(IntentParser.parse("good morning") is VoiceIntent.Unknown)
    }
}
