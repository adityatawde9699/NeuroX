package org.neurox.patient

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceIntentParserTest {
    @Test
    fun navigationCommandsSelectTheirIntendedDestination() {
        assertEquals(VoiceIntent.ListReminders, IntentParser.parse("open reminders"))
        assertEquals(VoiceIntent.StartActivity("sequence-recall"), IntentParser.parse("play sequence recall"))
        assertEquals(VoiceIntent.StartActivity("story-recall"), IntentParser.parse("start story recall"))
        assertEquals(VoiceIntent.StartActivity("daily-routine"), IntentParser.parse("daily routine"))
        assertTrue(IntentParser.parse("open the window") is VoiceIntent.Unknown)
        assertTrue(IntentParser.parse("doctor") is VoiceIntent.Unknown)
    }
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

    @Test
    fun regionalHelpPhrasesAreAlwaysSafetyIntents() {
        listOf("মোক সহায় কৰক", "জৰুৰী সহায়", "मुझे मदद चाहिए", "आपातकाल").forEach { phrase ->
            assertEquals(VoiceIntent.RequestHelp, IntentParser.parse(phrase, "as-IN"))
        }
    }

    @Test
    fun regionalReminderPhrasesRemainAllowlisted() {
        assertEquals(VoiceIntent.ListReminders, IntentParser.parse("মোৰ অনুস্মাৰক দেখুৱাওক", "as-IN"))
        assertEquals(VoiceIntent.ListReminders, IntentParser.parse("मेरे रिमाइंडर दिखाओ", "hi-IN"))
    }
}
