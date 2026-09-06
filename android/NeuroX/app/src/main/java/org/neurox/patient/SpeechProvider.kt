package org.neurox.patient

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer

// ──────────────────────────────────────────────
// Speech provider abstraction
// ──────────────────────────────────────────────

/**
 * A minimal, technology-agnostic speech-to-text interface.
 * Every provider must expose whether it can handle the current language
 * before starting a listening session, so the UI can show a clear
 * fallback message rather than silently failing.
 */
interface SpeechProvider {
    /** True if this provider can recognise speech for [languageCode]. */
    fun isSupported(languageCode: String): Boolean

    /**
     * Begin listening. Calls [onResult] with the top hypothesis once
     * recognition ends, or [onError] with a human-readable message.
     * Must be called on the main thread.
     */
    fun startListening(languageCode: String, onResult: (String) -> Unit, onError: (String) -> Unit)

    /** Cancel an in-progress listening session without reporting a result. */
    fun stopListening()
}

// ──────────────────────────────────────────────
// Mock provider (demo / tests — no hardware needed)
// ──────────────────────────────────────────────

/**
 * Returns a deterministic sequence of transcripts so the hackathon
 * demo always works offline and without real microphone input.
 *
 * Cycling through the phrases lets a demonstrator trigger each intent
 * by tapping the mic button in sequence.
 */
class MockSpeechProvider : SpeechProvider {
    private val phrases = listOf(
        "start memory match",
        "show my reminders",
        "I need help",
        "start object recall",
        "start pattern activity"
    )
    private var index = 0

    override fun isSupported(languageCode: String): Boolean = true

    override fun startListening(languageCode: String, onResult: (String) -> Unit, onError: (String) -> Unit) {
        // Simulate a short recognition delay, then return the next mock phrase.
        val result = phrases[index % phrases.size]
        index++
        // The caller supplies a coroutine scope; we call back synchronously here
        // because MockSpeechProvider is used only in controlled demo/test contexts.
        onResult(result)
    }

    override fun stopListening() { /* no-op */ }
}

// ──────────────────────────────────────────────
// Android on-device provider (SpeechRecognizer)
// ──────────────────────────────────────────────

/**
 * Uses Android's built-in [SpeechRecognizer] (Google on-device ASR).
 * Requires RECORD_AUDIO permission and Google Play Services.
 * Falls back gracefully when the device does not have a recogniser
 * available — [isSupported] will return false in that case.
 */
class AndroidSpeechProvider(private val context: Context) : SpeechProvider {
    private var recognizer: SpeechRecognizer? = null

    override fun isSupported(languageCode: String): Boolean =
        SpeechRecognizer.isRecognitionAvailable(context)

    override fun startListening(languageCode: String, onResult: (String) -> Unit, onError: (String) -> Unit) {
        stopListening() // ensure no stale session

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            onError("Speech recognition is not available on this device.")
            return
        }

        val sr = SpeechRecognizer.createSpeechRecognizer(context)
        recognizer = sr

        sr.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val top = matches?.firstOrNull()
                if (top != null) onResult(top)
                else onError("Could not understand. Please try again.")
            }

            override fun onError(error: Int) {
                val message = when (error) {
                    SpeechRecognizer.ERROR_NO_MATCH -> "Could not understand. Please try again."
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected. Please tap the microphone and speak."
                    SpeechRecognizer.ERROR_AUDIO -> "Microphone error. Please check your device microphone."
                    SpeechRecognizer.ERROR_NETWORK -> "Network error during speech recognition."
                    SpeechRecognizer.ERROR_NOT_SUPPORTED -> "Speech recognition is not supported for this language."
                    else -> "Speech recognition failed. Please try again."
                }
                onError(message)
            }
        })

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, languageCode)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, languageCode)
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_RESULTS, false)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
        }
        sr.startListening(intent)
    }

    override fun stopListening() {
        recognizer?.stopListening()
        recognizer?.destroy()
        recognizer = null
    }
}

// ──────────────────────────────────────────────
// Whisper provider stub (future remote ASR)
// ──────────────────────────────────────────────

/**
 * Stub for a future Whisper-compatible remote endpoint.
 * Always reports itself as unsupported until [baseUrl] is configured,
 * so the UI will show the correct fallback message rather than crashing.
 */
class WhisperSpeechProvider(private val baseUrl: String? = null) : SpeechProvider {
    override fun isSupported(languageCode: String): Boolean = baseUrl != null

    override fun startListening(languageCode: String, onResult: (String) -> Unit, onError: (String) -> Unit) {
        onError("Whisper speech provider is not configured. Set a base URL to enable it.")
    }

    override fun stopListening() { /* no-op */ }
}

// ──────────────────────────────────────────────
// Provider factory
// ──────────────────────────────────────────────

/**
 * Returns the best available [SpeechProvider] for the current context.
 * Priority: MockSpeechProvider in demo mode → AndroidSpeechProvider if available
 * → WhisperSpeechProvider stub (always unavailable until configured).
 *
 * Setting [demoMode] = true forces [MockSpeechProvider] regardless of
 * device capabilities, which is correct for hackathon demonstrations.
 */
fun buildSpeechProvider(context: Context, demoMode: Boolean = true): SpeechProvider =
    when {
        demoMode -> MockSpeechProvider()
        SpeechRecognizer.isRecognitionAvailable(context) -> AndroidSpeechProvider(context)
        else -> WhisperSpeechProvider()
    }
