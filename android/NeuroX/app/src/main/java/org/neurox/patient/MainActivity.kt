package org.neurox.patient

import android.os.Bundle
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { NeuroXApp() }
    }
}

private val Blue = Color(0xFF265FC5)

// ──────────────────────────────────────────────────────────────
// Root application composable
// ──────────────────────────────────────────────────────────────

@Composable
fun NeuroXApp() {
    val auth: PatientAuthViewModel = androidx.lifecycle.viewmodel.compose.viewModel()
    val state by auth.state.collectAsState()
    MaterialTheme(colorScheme = lightColorScheme(primary = Blue, background = Color(0xFFF8FAFD))) {
        when {
            state.checking -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            !state.signedIn -> PatientSignInScreen(state, auth::signIn)
            else -> PatientApp(auth.repository)
        }
    }
}

@Composable
fun PatientApp(repository: PatientRepository) {
    var tab by remember { mutableIntStateOf(0) }
    var showVoiceScreen by remember { mutableStateOf(false) }
    val viewModel: PatientViewModel = androidx.lifecycle.viewmodel.compose.viewModel(
        key = repository.patientId(),
        factory = PatientViewModel.factory(repository),
    )
    val ui by viewModel.state.collectAsState()
    LaunchedEffect(viewModel) { viewModel.refresh() }
    val context = LocalContext.current
    val microphonePermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) showVoiceScreen = true else viewModel.reportError()
    }
    val speechProvider = remember { buildSpeechProvider(context, demoMode = BuildConfig.DEBUG) }
    val languageCode = remember(ui.preferredLanguage) { languageNameToCode(ui.preferredLanguage) }
    val languageConfig = remember(languageCode, speechProvider) {
        languageConfigFor(languageCode).copy(
            speechSupported = languageConfigFor(languageCode).speechSupported &&
                speechProvider.isSupported(languageCode)
        )
    }

    if (showVoiceScreen) {
        VoiceListeningScreen(
            modifier = Modifier.fillMaxSize(),
            speechProvider = speechProvider,
            languageConfig = languageConfig,
            patientName = ui.patientName,
            activities = ui.activities,
            reminders = ui.reminders,
            onStartActivity = { activityId ->
                showVoiceScreen = false
                viewModel.start(
                    ui.activities.find { it.id == activityId }
                        ?: ui.activities.firstOrNull()
                        ?: defaultActivities.first()
                )
            },
            onNavigateToSafety = {
                showVoiceScreen = false
                tab = 3
            },
            onClose = { showVoiceScreen = false },
        )
        return
    }

    Scaffold(bottomBar = {
        NavigationBar {
            listOf(
                "Home" to Icons.Default.Home,
                "Activities" to Icons.Default.Favorite,
                "Reminders" to Icons.Default.Notifications,
                "Safety" to Icons.Default.Shield,
                "Profile" to Icons.Default.Person,
            ).forEachIndexed { index, (label, icon) ->
                NavigationBarItem(
                    selected = tab == index,
                    onClick = {
                        tab = index
                        viewModel.leaveActivity()
                    },
                    icon = { Icon(icon, label) },
                    label = { Text(label) },
                )
            }
        }
    }) { padding ->
        Column(Modifier.padding(padding)) {
            SyncBanner(
                ui.syncState,
                pendingCount = ui.pendingCount,
                lastSyncedLabel = ui.lastSyncedLabel,
                onRetry = viewModel::refresh,
            )
            when {
                ui.activeActivity == "memory-match" -> MemoryMatch(
                    Modifier.weight(1f),
                    onFinished = { attempts, responseTime, accuracy ->
                        viewModel.finish("memory-match", accuracy, responseTime, attempts)
                        tab = 1
                    },
                )
                ui.activeActivity == "object-recall" -> ObjectRecall(
                    Modifier.weight(1f),
                    onFinished = { attempts, responseTime, accuracy ->
                        viewModel.finish("object-recall", accuracy, responseTime, attempts)
                        tab = 1
                    },
                )
                tab == 0 -> Home(
                    Modifier.weight(1f),
                    patientName = ui.patientName,
                    safety = ui.safety,
                    reminders = ui.reminders,
                    languageConfig = languageConfig,
                    onStart = { viewModel.start(ui.activities.firstOrNull() ?: defaultActivities.first()) },
                    onOpenVoice = {
                        if (ContextCompat.checkSelfPermission(
                                context, Manifest.permission.RECORD_AUDIO
                            ) == PackageManager.PERMISSION_GRANTED
                        ) {
                            showVoiceScreen = true
                        } else {
                            microphonePermission.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    },
                )
                tab == 1 -> Activities(
                    Modifier.weight(1f), activities = ui.activities, onStart = viewModel::start
                )
                tab == 2 -> Reminders(
                    Modifier.weight(1f),
                    reminders = ui.reminders,
                    onComplete = viewModel::completeReminder,
                )
                tab == 3 -> Safety(
                    Modifier.weight(1f),
                    safety = ui.safety,
                    onHelp = { viewModel.sendHelp("I need help. Please check on me.") },
                    onSos = { viewModel.sendHelp() },
                )
                else -> Profile(Modifier.weight(1f), patientName = ui.patientName,
                    patientAge = ui.patientAge, languageConfig = languageConfig)
            }
        }
    }
}
