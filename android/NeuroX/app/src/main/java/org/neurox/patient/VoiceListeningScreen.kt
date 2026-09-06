package org.neurox.patient

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

// ──────────────────────────────────────────────
// Voice listening screen
// ──────────────────────────────────────────────

private val Blue = Color(0xFF265FC5)
private val Ink = Color(0xFF172033)
private val SafeGreen = Color(0xFF218567)

/**
 * Full-screen voice listening UI.
 *
 * Design decisions:
 * - Every voice action has a large equivalent touch button (Phase 4 exit criteria).
 * - If [languageConfig].speechSupported is false, the mic button is replaced
 *   by a clear explanation and the user is directed to touch actions only.
 * - The waveform is a simple animated bar visualisation that pulses while
 *   the provider is listening — no hardware waveform data is required.
 *
 * @param modifier           Layout modifier applied to the root Column.
 * @param speechProvider     Active SpeechProvider (Mock or Android).
 * @param languageConfig     Capability declaration for the patient's preferred language.
 * @param patientName        Used for personalised prompt text.
 * @param activities         Current activity list, used for touch-action buttons.
 * @param reminders          Today's reminders, shown in a sheet on ListReminders intent.
 * @param onStartActivity    Called when a StartActivity intent is resolved.
 * @param onNavigateToSafety Called when a RequestHelp intent is resolved.
 * @param onClose            Called when the user taps the back/close action.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceListeningScreen(
    modifier: Modifier = Modifier,
    speechProvider: SpeechProvider,
    languageConfig: LanguageConfig,
    patientName: String,
    activities: List<ActivityItem>,
    reminders: List<ReminderItem>,
    onStartActivity: (String?) -> Unit,
    onNavigateToSafety: () -> Unit,
    onClose: () -> Unit
) {
    var isListening by remember { mutableStateOf(false) }
    var transcript by remember { mutableStateOf("") }
    var statusMessage by remember { mutableStateOf("Tap the microphone and speak naturally.") }
    var resolvedIntent by remember { mutableStateOf<VoiceIntent?>(null) }
    var showRemindersSheet by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    // Pulsing animation while listening
    val infiniteTransition = rememberInfiniteTransition(label = "mic_pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.18f,
        animationSpec = infiniteRepeatable(
            animation = tween(700, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "mic_pulse_scale"
    )

    // Waveform bar heights (simulate audio energy)
    val barCount = 12
    val barAnimations = (0 until barCount).map { index ->
        val phase = (index * 40).toLong()
        infiniteTransition.animateFloat(
            initialValue = 0.15f,
            targetValue = if (isListening) 1f else 0.15f,
            animationSpec = infiniteRepeatable(
                animation = tween(
                    durationMillis = 450 + index * 30,
                    easing = FastOutSlowInEasing,
                    delayMillis = (phase % 300).toInt()
                ),
                repeatMode = RepeatMode.Reverse
            ),
            label = "bar_$index"
        )
    }

    fun handleResult(text: String) {
        isListening = false
        transcript = text
        val intent = IntentParser.parse(text, languageConfig.languageCode)
        resolvedIntent = intent
        statusMessage = IntentParser.describe(intent)
    }

    fun handleError(message: String) {
        isListening = false
        statusMessage = message
    }

    fun startListening() {
        if (!languageConfig.speechSupported || !speechProvider.isSupported(languageConfig.languageCode)) {
            statusMessage = "Speech is not available for ${languageConfig.languageName}. Use the touch options below."
            return
        }
        isListening = true
        transcript = ""
        resolvedIntent = null
        statusMessage = "Listening…"
        scope.launch {
            speechProvider.startListening(
                languageCode = languageConfig.languageCode,
                onResult = ::handleResult,
                onError = ::handleError
            )
        }
    }

    fun executeIntent(intent: VoiceIntent) {
        when (intent) {
            is VoiceIntent.StartActivity -> onStartActivity(intent.activityId)
            is VoiceIntent.ListReminders -> showRemindersSheet = true
            is VoiceIntent.RequestHelp   -> onNavigateToSafety()
            is VoiceIntent.Unknown       -> {
                // Keep on screen; user can tap again or use touch actions below
                statusMessage = "Not sure I understood. Try again or tap an option below."
            }
        }
    }

    // ── Reminders bottom sheet ─────────────────────────────────────────
    if (showRemindersSheet) {
        ModalBottomSheet(onDismissRequest = { showRemindersSheet = false }) {
            Column(Modifier.padding(horizontal = 24.dp, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Today's Reminders", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                if (reminders.isEmpty()) {
                    Text("No reminders for today.", color = Color.Gray)
                } else {
                    reminders.forEach { reminder ->
                        Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0xFFF0F5FA))) {
                            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Notifications, null, tint = if (reminder.completed) SafeGreen else Blue)
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(reminder.title, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                                    Text(reminder.scheduledTime.take(16).replace("T", " "), color = Color.Gray, fontSize = 14.sp)
                                }
                                Text(if (reminder.completed) "Done" else "Upcoming", color = if (reminder.completed) SafeGreen else Blue, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                            }
                        }
                    }
                }
                Button(onClick = { showRemindersSheet = false }, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                    Text("Close", fontSize = 17.sp)
                }
                Spacer(Modifier.height(24.dp))
            }
        }
    }

    // ── Main screen layout ─────────────────────────────────────────────
    Column(
        modifier = modifier.fillMaxSize().background(Color(0xFFF8FAFD)).verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // ── Top bar ──────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onClose) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Go back", tint = Ink)
            }
            Text("Talk to NeuroX", modifier = Modifier.weight(1f), fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Ink)
        }

        Spacer(Modifier.height(8.dp))

        // ── Language capability card ──────────────────────────────────
        LanguageCapabilityCard(languageConfig)

        Spacer(Modifier.height(28.dp))

        // ── Personalised prompt ───────────────────────────────────────
        Text(
            text = "Hello, $patientName.",
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            color = Ink
        )
        Text(
            text = if (languageConfig.speechSupported) "Speak naturally, I'm listening."
                   else "Voice is not available for ${languageConfig.languageName}. Use the options below.",
            fontSize = 17.sp,
            color = Color.Gray,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 32.dp, vertical = 6.dp)
        )

        Spacer(Modifier.height(24.dp))

        // ── Waveform visualisation ────────────────────────────────────
        if (isListening) {
            Row(
                modifier = Modifier.height(54.dp).padding(horizontal = 32.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                barAnimations.forEach { barHeight ->
                    Box(
                        modifier = Modifier
                            .width(6.dp)
                            .fillMaxHeight(barHeight.value)
                            .clip(RoundedCornerShape(3.dp))
                            .background(Blue.copy(alpha = 0.6f + barHeight.value * 0.4f))
                    )
                }
            }
        } else {
            Spacer(Modifier.height(54.dp))
        }

        Spacer(Modifier.height(20.dp))

        // ── Microphone button ─────────────────────────────────────────
        if (languageConfig.speechSupported) {
            val micScale = if (isListening) pulseScale else 1f
            FilledIconButton(
                onClick = {
                    if (isListening) {
                        speechProvider.stopListening()
                        isListening = false
                        statusMessage = "Stopped. Tap the microphone to try again."
                    } else {
                        startListening()
                    }
                },
                modifier = Modifier.size(100.dp).scale(micScale),
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = if (isListening) Color(0xFFBD3E39) else Blue,
                    contentColor = Color.White
                )
            ) {
                Icon(
                    if (isListening) Icons.Default.Stop else Icons.Default.Mic,
                    contentDescription = if (isListening) "Stop listening" else "Start listening",
                    modifier = Modifier.size(48.dp)
                )
            }
            Spacer(Modifier.height(12.dp))
            Text(
                text = if (isListening) "Tap to stop" else "Tap to speak",
                fontSize = 15.sp,
                color = Color.Gray
            )
        }

        Spacer(Modifier.height(16.dp))

        // ── Transcript display ────────────────────────────────────────
        if (transcript.isNotEmpty()) {
            Card(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F0FF)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text("You said:", fontSize = 13.sp, color = Color.Gray)
                    Text(transcript, fontSize = 18.sp, color = Ink, fontWeight = FontWeight.Medium, modifier = Modifier.padding(top = 4.dp))
                }
            }
            Spacer(Modifier.height(10.dp))
        }

        // ── Status / confirmation message ─────────────────────────────
        Text(
            text = statusMessage,
            fontSize = 16.sp,
            color = if (resolvedIntent is VoiceIntent.Unknown) Color(0xFFB65A38) else Color.Gray,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 28.dp)
        )

        Spacer(Modifier.height(20.dp))

        // ── Intent action buttons (after recognition) ─────────────────
        if (resolvedIntent != null && resolvedIntent !is VoiceIntent.Unknown) {
            Button(
                onClick = { resolvedIntent?.let(::executeIntent) },
                modifier = Modifier.fillMaxWidth(0.72f).height(58.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                Icon(Icons.Default.PlayArrow, null, Modifier.size(24.dp))
                Spacer(Modifier.width(8.dp))
                Text("Continue", fontSize = 18.sp)
            }
            Spacer(Modifier.height(10.dp))
        }

        if (!isListening && languageConfig.speechSupported) {
            OutlinedButton(
                onClick = { startListening() },
                modifier = Modifier.fillMaxWidth(0.72f).height(52.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                Icon(Icons.Default.Refresh, null)
                Spacer(Modifier.width(8.dp))
                Text("Speak Again", fontSize = 17.sp)
            }
        }

        Spacer(Modifier.height(28.dp))
        HorizontalDivider(modifier = Modifier.padding(horizontal = 24.dp), color = Color(0xFFE0E8F0))
        Spacer(Modifier.height(20.dp))

        // ── Touch equivalents (always visible) ────────────────────────
        Text("Or tap an option:", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Ink)
        Spacer(Modifier.height(14.dp))

        TouchIntentCard(
            label = "Start today's activity",
            sublabel = activities.firstOrNull()?.title ?: "Memory Match",
            icon = Icons.Default.PlayArrow,
            color = Blue
        ) { onStartActivity(activities.firstOrNull()?.id) }

        TouchIntentCard(
            label = "Show reminders",
            sublabel = "${reminders.count { !it.completed }} upcoming today",
            icon = Icons.Default.Notifications,
            color = Blue
        ) { showRemindersSheet = true }

        TouchIntentCard(
            label = "I Need Help",
            sublabel = "Open Safety screen",
            icon = Icons.Default.Shield,
            color = SafeGreen
        ) { onNavigateToSafety() }

        Spacer(Modifier.height(32.dp))
    }
}

// ──────────────────────────────────────────────
// Supporting composables
// ──────────────────────────────────────────────

/**
 * Displays the patient's configured language and its capability status.
 * A clear fallback note is shown when TTS is not available.
 */
@Composable
private fun LanguageCapabilityCard(config: LanguageConfig) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF0F5FA)),
        shape = RoundedCornerShape(14.dp)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Language, contentDescription = null, tint = Blue, modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(config.languageName, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 5.dp)) {
                    CapabilityPill("Speech", config.speechSupported)
                    CapabilityPill("Voice guides", config.ttsSupported)
                    if (config.bhashinSupported) {
                        CapabilityPill("BHASHINI", supported = true)
                    }
                }
                if (config.ttsFallbackNote != null) {
                    Text(config.ttsFallbackNote, fontSize = 12.sp, color = Color(0xFF7A6A3A), modifier = Modifier.padding(top = 4.dp))
                }
                if (config.bhashinSupported && config.bhashinNote != null) {
                    Text(config.bhashinNote, fontSize = 12.sp, color = Color(0xFF2A5AA8), modifier = Modifier.padding(top = 3.dp))
                }
            }
        }
    }
}

@Composable
private fun CapabilityPill(label: String, supported: Boolean) {
    val bg = if (supported) Color(0xFFD4EDDA) else Color(0xFFFFF3CD)
    val text = if (supported) Color(0xFF218567) else Color(0xFF7A6A3A)
    val icon = if (supported) Icons.Default.CheckCircle else Icons.Default.Info
    Surface(color = bg, shape = RoundedCornerShape(8.dp)) {
        Row(Modifier.padding(horizontal = 8.dp, vertical = 3.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Icon(icon, null, tint = text, modifier = Modifier.size(12.dp))
            Text("$label: ${if (supported) "✓" else "fallback"}", fontSize = 12.sp, color = text, fontWeight = FontWeight.SemiBold)
        }
    }
}

/**
 * A large, accessible touch-action card used as the voice alternative.
 * Meets the 48dp minimum touch target requirement.
 */
@Composable
private fun TouchIntentCard(
    label: String,
    sublabel: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: Color,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 5.dp),
        shape = RoundedCornerShape(16.dp),
        onClick = onClick
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = label, tint = color, modifier = Modifier.size(32.dp))
            Spacer(Modifier.width(16.dp))
            Column(Modifier.weight(1f)) {
                Text(label, fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                Text(sublabel, fontSize = 14.sp, color = Color.Gray)
            }
            Icon(Icons.Default.ChevronRight, null, tint = Color.Gray)
        }
    }
}
