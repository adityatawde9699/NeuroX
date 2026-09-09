package org.neurox.patient

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Blue = Color(0xFF265FC5)
private val Ink = Color(0xFF172033)
private val SafeGreen = Color(0xFF218567)

// ──────────────────────────────────────────────────────────────
// Sync banner (Phase 5: pending count + last-synced label)
// ──────────────────────────────────────────────────────────────

@Composable
internal fun SyncBanner(
    state: SyncState,
    pendingCount: Int = 0,
    lastSyncedLabel: String? = null,
    onRetry: () -> Unit
) {
    // Synced state: show a brief confirmation label if available, then nothing.
    if (state == SyncState.Synced && lastSyncedLabel == null) return
    val (bg, message) = when (state) {
        SyncState.Loading -> Color(0xFFE8F0FF) to "Loading your NeuroX data…"
        SyncState.Synced  -> Color(0xFFE8F5EE) to "Synced · $lastSyncedLabel"
        SyncState.Offline -> Color(0xFFFFF0ED) to (
            if (pendingCount > 0)
                "Working offline · $pendingCount item${if (pendingCount == 1) "" else "s"} saved — will sync when connected"
            else
                "Working offline · Showing saved activities"
        )
        SyncState.Error   -> Color(0xFFFFF0ED) to "Could not sync your data"
    }
    Surface(color = bg, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(message, modifier = Modifier.weight(1f), color = Ink)
            if (state != SyncState.Loading && state != SyncState.Synced)
                TextButton(onClick = onRetry) { Text("Retry") }
        }
    }
}

// ──────────────────────────────────────────────────────────────
// Home screen — now wires the voice button
// ──────────────────────────────────────────────────────────────

@Composable
internal fun Home(
    modifier: Modifier,
    patientName: String,
    safety: SafetyState?,
    reminders: List<ReminderItem>,
    languageConfig: LanguageConfig,
    onStart: () -> Unit,
    onOpenVoice: () -> Unit
) = Column(
    modifier.fillMaxSize().padding(24.dp),
    verticalArrangement = Arrangement.spacedBy(18.dp)
) {
    Text("Good Morning", fontSize = 20.sp, color = Color.Gray)
    Text(patientName, fontSize = 36.sp, fontWeight = FontWeight.Bold, color = Ink)

    // "Talk to NeuroX" card — now navigates to the listening screen
    Card(
        colors = CardDefaults.cardColors(containerColor = Blue),
        shape = RoundedCornerShape(24.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Talk to NeuroX", color = Color.White, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(13.dp))
            FilledIconButton(
                onClick = onOpenVoice,
                modifier = Modifier.size(78.dp),
                colors = IconButtonDefaults.filledIconButtonColors(containerColor = Color.White, contentColor = Blue)
            ) {
                Icon(Icons.Default.Mic, "Talk to NeuroX", Modifier.size(38.dp))
            }
            Spacer(Modifier.height(10.dp))
            Text("Tap and speak naturally", color = Color.White.copy(.88f), fontSize = 16.sp)
            // Language capability note
            if (!languageConfig.ttsSupported) {
                Spacer(Modifier.height(6.dp))
                Surface(
                    color = Color.White.copy(alpha = 0.18f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        "Voice guides: English fallback",
                        color = Color.White,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }
        }
    }

    Button(
        onClick = onStart,
        modifier = Modifier.fillMaxWidth().height(68.dp),
        shape = RoundedCornerShape(18.dp)
    ) {
        Icon(Icons.Default.PlayArrow, null, Modifier.size(30.dp))
        Spacer(Modifier.width(10.dp))
        Text("Start Today's Activity", fontSize = 19.sp)
    }

    Text("Today's reminders", fontSize = 21.sp, fontWeight = FontWeight.Bold)
    if (reminders.isEmpty()) {
        Text("No reminders for today.", color = Color.Gray)
    } else {
        reminders.take(3).forEach { reminder ->
            ReminderCard(
                title = reminder.title,
                time = reminder.scheduledTime.take(16).replace("T", " "),
                status = if (reminder.completed) "Done" else "Upcoming",
                color = if (reminder.completed) SafeGreen else Blue
            )
        }
    }
    StatusCard(safety?.status ?: "Safety status unavailable", "Last reported status", Icons.Default.Shield, Blue)
}

// ──────────────────────────────────────────────────────────────
// Activities screen
// ──────────────────────────────────────────────────────────────

@Composable
internal fun Activities(modifier: Modifier, activities: List<ActivityItem>, onStart: (ActivityItem) -> Unit) =
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) {
        Text("Activities", fontSize = 31.sp, fontWeight = FontWeight.Bold)
        Text("Choose one activity for today.", color = Color.Gray, fontSize = 17.sp)
        if (activities.isEmpty()) Text("No activities are available right now.", color = Color.Gray)
        activities.forEach { activity ->
            ActivityCard(
                title = activity.title,
                detail = activity.description,
                icon = when (activity.id) {
                    "memory-match"  -> Icons.Default.GridView
                    "object-recall" -> Icons.Default.Visibility
                    else            -> Icons.Default.Extension
                },
                level = "Level ${activity.difficulty}"
            ) { onStart(activity) }
        }
    }

// ──────────────────────────────────────────────────────────────
// Memory Match game
// ──────────────────────────────────────────────────────────────

@Composable
internal fun MemoryMatch(modifier: Modifier, onFinished: (Int, Float, Float) -> Unit) {
    val startedAt = remember { System.currentTimeMillis() }
    var first by remember { mutableStateOf<Int?>(null) }
    var matched by remember { mutableStateOf(setOf<Int>()) }
    var attempts by remember { mutableIntStateOf(0) }
    val symbols = listOf("☀", "☀", "☕", "☕")
    val complete = matched.size == 4
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text("Memory Match", fontSize = 29.sp, fontWeight = FontWeight.Bold)
        LinearProgressIndicator(progress = { matched.size / 4f }, modifier = Modifier.fillMaxWidth())
        Text(if (complete) "Well done, Maya!" else "Find the matching pictures.", fontSize = 19.sp, color = Color.Gray)
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            (0..1).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    (0..1).forEach { col ->
                        val index = row * 2 + col
                        val revealed = index in matched || index == first
                        Card(
                            modifier = Modifier.weight(1f).height(125.dp).clickable(enabled = !complete && index !in matched) {
                                if (first == null) first = index
                                else {
                                    attempts++
                                    val selected = first!!
                                    if (symbols[selected] == symbols[index] && selected != index) matched = matched + selected + index
                                    first = null
                                }
                            },
                            colors = CardDefaults.cardColors(containerColor = if (revealed) Color(0xFFE8F0FF) else Blue),
                            shape = RoundedCornerShape(18.dp)
                        ) {
                            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text(if (revealed) symbols[index] else "?", fontSize = 46.sp, color = if (revealed) Ink else Color.White)
                            }
                        }
                    }
                }
            }
        }
        if (complete) {
            val responseSeconds = ((System.currentTimeMillis() - startedAt) / 1000f).coerceAtLeast(.1f)
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5EE)), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.CheckCircle, null, tint = SafeGreen, modifier = Modifier.size(38.dp))
                    Text("Activity complete", fontSize = 21.sp, fontWeight = FontWeight.Bold)
                    Text("Attempts: $attempts · Time: ${"%.1f".format(responseSeconds)} sec", color = Color.DarkGray, textAlign = TextAlign.Center)
                    Text("Your next activity is adjusted to your performance.", color = Color.DarkGray, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 6.dp))
                    Button(onClick = { onFinished(attempts, responseSeconds, 1f) }, modifier = Modifier.padding(top = 10.dp)) { Text("Continue") }
                }
            }
        }
    }
}

// ──────────────────────────────────────────────────────────────
// Object Recall game
// ──────────────────────────────────────────────────────────────

@Composable
internal fun ObjectRecall(modifier: Modifier, onFinished: (Int, Float, Float) -> Unit) {
    var step by remember { mutableIntStateOf(0) }
    var result by remember { mutableStateOf<Boolean?>(null) }
    val startedAt = remember { System.currentTimeMillis() }
    val objects = listOf("☕ Cup", "🔑 Key", "📚 Book")
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text("Remember the Objects", fontSize = 29.sp, fontWeight = FontWeight.Bold)
        LinearProgressIndicator(progress = { if (step == 0) .35f else .75f }, modifier = Modifier.fillMaxWidth())
        if (step == 0) {
            Text("Please look at these objects.", fontSize = 20.sp, color = Color.Gray)
            objects.forEach { objectName ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Text(objectName, modifier = Modifier.padding(19.dp), fontSize = 23.sp, fontWeight = FontWeight.SemiBold)
                }
            }
            Button(onClick = { step = 1 }, modifier = Modifier.fillMaxWidth().height(65.dp), shape = RoundedCornerShape(18.dp)) {
                Text("I am ready", fontSize = 19.sp)
            }
        } else if (result == null) {
            Text("Which object did you see?", fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
            Text("Choose the cup.", color = Color.Gray, fontSize = 17.sp)
            listOf("☕ Cup" to true, "🌼 Flower" to false, "🚲 Bicycle" to false).forEach { (choice, correct) ->
                OutlinedButton(
                    onClick = { result = correct },
                    modifier = Modifier.fillMaxWidth().height(64.dp),
                    shape = RoundedCornerShape(16.dp)
                ) { Text(choice, fontSize = 20.sp) }
            }
        } else {
            val responseSeconds = ((System.currentTimeMillis() - startedAt) / 1000f).coerceAtLeast(.1f)
            Card(
                colors = CardDefaults.cardColors(containerColor = if (result == true) Color(0xFFE8F5EE) else Color(0xFFFFF0ED)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(22.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(if (result == true) Icons.Default.CheckCircle else Icons.Default.Info, null, tint = if (result == true) SafeGreen else Color(0xFFB65A38), modifier = Modifier.size(42.dp))
                    Text(if (result == true) "Well done, Maya!" else "That is okay. Let's try again tomorrow.", fontSize = 21.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 9.dp))
                    Text("Response time: ${"%.1f".format(responseSeconds)} sec", color = Color.DarkGray, modifier = Modifier.padding(top = 6.dp))
                    Text("Your next activity is adjusted to your performance.", color = Color.DarkGray, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp))
                    Button(onClick = { onFinished(1, responseSeconds, if (result == true) 1f else 0f) }, modifier = Modifier.padding(top = 14.dp)) { Text("Continue") }
                }
            }
        }
    }
}

// ──────────────────────────────────────────────────────────────
// Reminders screen
// ──────────────────────────────────────────────────────────────

@Composable
internal fun Reminders(modifier: Modifier, reminders: List<ReminderItem>, onComplete: (String) -> Unit) =
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) {
        Text("Reminders", fontSize = 31.sp, fontWeight = FontWeight.Bold)
        Text("Today", color = Color.Gray, fontSize = 17.sp)
        if (reminders.isEmpty()) Text("No reminders for today.", color = Color.Gray)
        else reminders.forEach { reminder ->
            ReminderCard(
                title = reminder.title,
                time = reminder.scheduledTime.take(16).replace("T", " "),
                status = if (reminder.completed) "Done" else "Tap when done",
                color = if (reminder.completed) SafeGreen else Blue
            ) { if (!reminder.completed) onComplete(reminder.id) }
        }
    }

// ──────────────────────────────────────────────────────────────
// Safety screen
// ──────────────────────────────────────────────────────────────

@Composable
internal fun Safety(modifier: Modifier, safety: SafetyState?, onHelp: () -> Unit, onSos: () -> Unit) = Column(
    modifier.fillMaxSize().padding(24.dp),
    verticalArrangement = Arrangement.spacedBy(18.dp)
) {
    Text("Safety", fontSize = 31.sp, fontWeight = FontWeight.Bold)
    StatusCard(safety?.status ?: "Safety status unavailable", "Last reported status", Icons.Default.Shield, Blue)
    val expectedReturn = safety?.settings?.expectedReturnAt?.let { value ->
        runCatching {
            java.time.OffsetDateTime.parse(value).atZoneSameInstant(java.time.ZoneId.systemDefault())
                .format(java.time.format.DateTimeFormatter.ofLocalizedDateTime(java.time.format.FormatStyle.SHORT))
        }.getOrDefault("Unavailable")
    } ?: "Not set"
    StatusCard("Expected return", expectedReturn, Icons.Default.Schedule, Blue)
    OutlinedButton(onClick = onHelp, modifier = Modifier.fillMaxWidth().height(62.dp)) {
        Icon(Icons.Default.Phone, null)
        Spacer(Modifier.width(10.dp))
        Text("I Need Help", fontSize = 18.sp)
    }
    Button(onClick = onSos, modifier = Modifier.fillMaxWidth().height(70.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFBD3E39))) {
        Icon(Icons.Default.Warning, null)
        Spacer(Modifier.width(10.dp))
        Text("SOS", fontSize = 22.sp)
    }
    safety?.contacts?.take(2)?.forEach { contact ->
        StatusCard(contact.name, "${contact.relationship} · ${contact.phone}", Icons.Default.Phone, Blue)
    }
}

// ──────────────────────────────────────────────────────────────
// Profile screen — shows language capability
// ──────────────────────────────────────────────────────────────

@Composable
internal fun Profile(modifier: Modifier, patientName: String, patientAge: Int?, languageConfig: LanguageConfig) = Column(
    modifier.fillMaxSize().padding(24.dp),
    verticalArrangement = Arrangement.spacedBy(16.dp)
) {
    Text("My Profile", fontSize = 31.sp, fontWeight = FontWeight.Bold)
    val ageLabel = patientAge?.let { "$it years · " } ?: ""
    StatusCard(patientName.ifBlank { "Profile unavailable" }, "${ageLabel}Preferred language: ${languageConfig.languageName}", Icons.Default.Person, Blue)

    // Language capability card
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF0F5FA)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Language, null, tint = Blue, modifier = Modifier.size(22.dp))
                Spacer(Modifier.width(10.dp))
                Text("Language & Voice", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = Ink)
            }
            Text(languageConfig.languageName, fontSize = 15.sp, color = Ink)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                CapabilityChip("Speech", languageConfig.speechSupported)
                CapabilityChip("Voice guides", languageConfig.ttsSupported)
            }
            if (languageConfig.ttsFallbackNote != null) {
                Text(languageConfig.ttsFallbackNote, fontSize = 13.sp, color = Color(0xFF7A6A3A))
            }
        }
    }
}

@Composable
private fun CapabilityChip(label: String, supported: Boolean) {
    val bg = if (supported) Color(0xFFD4EDDA) else Color(0xFFFFF3CD)
    val text = if (supported) Color(0xFF218567) else Color(0xFF7A6A3A)
    Surface(color = bg, shape = RoundedCornerShape(8.dp)) {
        Text(
            "$label: ${if (supported) "✓ Available" else "⚠ Fallback"}",
            fontSize = 13.sp,
            color = text,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
        )
    }
}

// ──────────────────────────────────────────────────────────────
// Shared UI components
// ──────────────────────────────────────────────────────────────

@Composable
private fun ActivityCard(title: String, detail: String, icon: androidx.compose.ui.graphics.vector.ImageVector, level: String, onClick: () -> Unit = {}) =
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.padding(19.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = Blue, modifier = Modifier.size(34.dp))
            Spacer(Modifier.width(16.dp))
            Column(Modifier.weight(1f)) { Text(title, fontSize = 19.sp, fontWeight = FontWeight.SemiBold); Text(detail, color = Color.Gray) }
            Text(level, color = Blue, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
        }
    }

@Composable
private fun ReminderCard(title: String, time: String, status: String, color: Color, onClick: () -> Unit = {}) =
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.padding(17.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Notifications, null, tint = color)
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) { Text(title, fontSize = 18.sp, fontWeight = FontWeight.SemiBold); Text(time, color = Color.Gray) }
            Text(status, color = color, fontWeight = FontWeight.SemiBold)
        }
    }

@Composable
private fun StatusCard(title: String, detail: String, icon: androidx.compose.ui.graphics.vector.ImageVector, color: Color) =
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFF0F5FA)), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(17.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = color)
            Spacer(Modifier.width(12.dp))
            Column { Text(title, fontSize = 18.sp, fontWeight = FontWeight.Bold); Text(detail, color = Color.DarkGray) }
        }
    }
