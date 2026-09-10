package org.neurox.patient

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException
import java.time.Instant
import java.util.UUID

private const val DEFAULT_CONTENT_VERSION = "2026.09-v1"
val defaultActivities = listOf(
    ActivityItem("memory-match", "Memory Match", "Find two matching familiar objects.", 2, DEFAULT_CONTENT_VERSION),
    ActivityItem("object-recall", "Remember the Objects", "Look, listen, then remember.", 2, DEFAULT_CONTENT_VERSION),
    ActivityItem("pattern", "Pattern Completion", "Choose what comes next.", 2, DEFAULT_CONTENT_VERSION),
    ActivityItem("sequence-recall", "Sequence Recall", "Remember a short order of familiar daily items.", 2, DEFAULT_CONTENT_VERSION),
    ActivityItem("daily-routine", "Daily Routine Recall", "Put a familiar morning routine in a helpful order.", 2, DEFAULT_CONTENT_VERSION),
    ActivityItem("story-recall", "Story Recall", "Listen to a short everyday story and remember one detail.", 2, DEFAULT_CONTENT_VERSION),
)

enum class SyncState { Loading, Synced, Offline, Error }

data class PatientUiState(
    val activities: List<ActivityItem> = defaultActivities,
    val reminders: List<ReminderItem> = emptyList(),
    val safety: SafetyState? = null,
    val patientName: String = "",
    val patientAge: Int? = null,
    val preferredLanguage: String = "Assamese",
    val activeActivity: String? = null,
    val syncState: SyncState = SyncState.Loading,
    val pendingCount: Int = 0,
    val lastSyncedLabel: String? = null,
    val privacy: PrivacyState = PrivacyState(),
    val caregivers: List<CaregiverAccess> = emptyList(),
    val privacyBusy: Boolean = false,
    val privacyMessage: String? = null,
)

class PatientViewModel(
    private val repository: PatientRepository,
    private val savedState: SavedStateHandle = SavedStateHandle(),
) : ViewModel() {
    private val completeActivity = CompleteActivity(repository)
    private val completeReminder = CompleteReminder(repository)
    private val sendHelp = SendHelp(repository)
    private val mutableState = MutableStateFlow(
        PatientUiState(activeActivity = savedState["active_activity"])
    )
    val state = mutableState.asStateFlow()
    private var activeEventId: String? = savedState["active_event_id"]
    private var activeStartedAt: String? = savedState["active_started_at"]
    private var interruptions: Int = savedState["activity_interruptions"] ?: 0
    private var refreshJob: Job? = null
    private var startJob: Job? = null

    init {
        repository.schedulePendingSync()
        refresh()
    }

    fun refresh() {
        if (refreshJob?.isActive == true) return
        refreshJob = viewModelScope.launch {
            mutableState.update { it.copy(syncState = SyncState.Loading) }
            try {
                applyData(repository.load(), SyncState.Synced)
                val pendingCount = repository.pendingEventCount()
                mutableState.update { it.copy(
                    pendingCount = pendingCount, lastSyncedLabel = "just now"
                ) }
                loadPrivacy()
            } catch (error: CancellationException) {
                throw error
            } catch (_: IOException) {
                recoverOffline {
                    repository.cachedData()?.let { applyData(it, SyncState.Offline) }
                }
            } catch (_: Exception) {
                mutableState.update { it.copy(syncState = SyncState.Error) }
            }
        }
    }

    fun start(activity: ActivityItem) {
        if (startJob?.isActive == true || state.value.activeActivity != null) return
        startJob = viewModelScope.launch {
            val eventId = UUID.randomUUID().toString()
            val startedAt = Instant.now().toString()
            activeEventId = eventId
            activeStartedAt = startedAt
            savedState["active_event_id"] = eventId
            savedState["active_started_at"] = startedAt
            interruptions = 0
            savedState["activity_interruptions"] = 0
            try {
                repository.startActivity(activity, eventId, startedAt, false)
            } catch (error: CancellationException) {
                throw error
            } catch (_: IOException) {
                mutableState.update { it.copy(syncState = SyncState.Offline) }
            } catch (_: Exception) {
                mutableState.update { it.copy(syncState = SyncState.Error) }
                return@launch
            }
            savedState["active_activity"] = activity.id
            mutableState.update { it.copy(activeActivity = activity.id) }
        }
    }

    fun leaveActivity() {
        startJob?.cancel()
        activeEventId = null
        activeStartedAt = null
        savedState["active_activity"] = null
        savedState["active_event_id"] = null
        savedState["active_started_at"] = null
        savedState["activity_interruptions"] = null
        mutableState.update { it.copy(activeActivity = null) }
    }

    fun recordInterruption() {
        if (state.value.activeActivity == null) return
        interruptions = (interruptions + 1).coerceAtMost(100)
        savedState["activity_interruptions"] = interruptions
    }

    fun finish(activityId: String, accuracy: Float, responseTime: Float, attempts: Int) {
        if (state.value.activeActivity != activityId) return
        val activity = state.value.activities.firstOrNull { it.id == activityId } ?: return
        val eventId = activeEventId ?: UUID.randomUUID().toString()
        val completion = ActivityCompletionRequest(
            userId = repository.patientId(), activityId = activity.id,
            startedAt = activeStartedAt ?: Instant.now().minusSeconds(responseTime.toLong()).toString(),
            completedAt = Instant.now().toString(), accuracy = accuracy,
            responseTime = responseTime.coerceAtLeast(.1f), attempts = attempts.coerceAtLeast(1),
            difficultyLevel = activity.difficulty, eventId = eventId,
            contentVersion = activity.contentVersion, interruptions = interruptions,
        )
        activeEventId = null
        activeStartedAt = null
        leaveActivity()
        viewModelScope.launch {
            try {
                val delivery = completeActivity(activity, completion)
                if (delivery is Delivery.Queued) {
                    recoverOffline { }
                    return@launch
                }
                val result = (delivery as Delivery.Online).value
                mutableState.update { current -> current.copy(
                    activities = result.nextDifficulty?.let { level ->
                        current.activities.map { if (it.id == activity.id) it.copy(difficulty = level.coerceIn(1, 5)) else it }
                    } ?: current.activities,
                    syncState = SyncState.Synced,
                ) }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                mutableState.update { it.copy(syncState = SyncState.Error) }
            }
        }
    }

    fun completeReminder(id: String) = viewModelScope.launch {
        try {
            when (val delivery = completeReminder.invoke(id)) {
                is Delivery.Online -> applyData(delivery.value, SyncState.Synced)
                Delivery.Queued -> recoverOffline {
                    mutableState.update { current -> current.copy(
                        reminders = current.reminders.map { if (it.id == id) it.copy(completed = true) else it },
                    ) }
                }
            }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(syncState = SyncState.Error) }
        }
    }

    fun snoozeReminder(id: String) = viewModelScope.launch {
        val snoozedUntil = java.time.Instant.now().plusSeconds(600).toString()
        try {
            val reminder = repository.updateReminderState(id, "snoozed", snoozedUntil)
            mutableState.update { current -> current.copy(
                reminders = current.reminders.map { if (it.id == id) reminder else it },
                syncState = SyncState.Synced,
            ) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: java.io.IOException) {
            try {
                repository.queueReminderState(id, "snoozed", snoozedUntil)
                repository.updateReminderStateLocally(id, "snoozed", snoozedUntil)
                recoverOffline {
                    mutableState.update { current -> current.copy(
                        reminders = current.reminders.map {
                            if (it.id == id) it.copy(status = "snoozed", snoozedUntil = snoozedUntil) else it
                        },
                    ) }
                }
            } catch (_: Exception) {
                mutableState.update { it.copy(syncState = SyncState.Error) }
            }
        } catch (_: Exception) {
            mutableState.update { it.copy(syncState = SyncState.Error) }
        }
    }

    fun sendHelp(message: String = "I need help. Please check on me.") = viewModelScope.launch {
        val request = SosRequest(message)
        try {
            when (sendHelp.invoke(request)) {
                is Delivery.Online -> mutableState.update { it.copy(syncState = SyncState.Synced) }
                Delivery.Queued -> recoverOffline { }
            }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(syncState = SyncState.Error) }
        }
    }

    fun reportError() = mutableState.update { it.copy(syncState = SyncState.Error) }

    fun setLocationSharing(enabled: Boolean) = viewModelScope.launch {
        mutableState.update { it.copy(privacyBusy = true, privacyMessage = null) }
        try {
            val response = repository.setLocationSharing(enabled)
            mutableState.update { it.copy(
                privacy = it.privacy.copy(locationSharingEnabled = response.enabled),
                privacyBusy = false, privacyMessage = response.message,
            ) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(privacyBusy = false, privacyMessage = "Privacy setting could not be changed.") }
        }
    }

    fun revokeCaregiver(caregiverId: String) = viewModelScope.launch {
        mutableState.update { it.copy(privacyBusy = true, privacyMessage = null) }
        try {
            repository.revokeCaregiver(caregiverId)
            mutableState.update { it.copy(
                caregivers = it.caregivers.filterNot { person -> person.id == caregiverId },
                privacyBusy = false, privacyMessage = "Caregiver access was revoked immediately.",
            ) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(privacyBusy = false, privacyMessage = "Caregiver access could not be changed.") }
        }
    }

    fun setConsent(purpose: String, granted: Boolean) = viewModelScope.launch {
        mutableState.update { it.copy(privacyBusy = true, privacyMessage = null) }
        try {
            val response = repository.setConsent(purpose, granted)
            val consent = ConsentState(response.granted, response.noticeVersion, Instant.now().toString())
            mutableState.update { it.copy(
                privacy = it.privacy.copy(consents = it.privacy.consents + (purpose to consent)),
                caregivers = if (purpose == "caregiver_access" && !granted) emptyList() else it.caregivers,
                privacyBusy = false, privacyMessage = "Your consent choice was saved.",
            ) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(privacyBusy = false, privacyMessage = "Consent choice could not be saved.") }
        }
    }

    private suspend fun loadPrivacy() {
        try {
            val privacy = repository.privacy()
            val caregivers = repository.caregivers()
            mutableState.update { it.copy(privacy = privacy, caregivers = caregivers) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            mutableState.update { it.copy(privacyMessage = "Privacy controls need a connection to load.") }
        }
    }

    private suspend fun recoverOffline(action: suspend () -> Unit) {
        try {
            action()
            val pendingCount = repository.pendingEventCount()
            mutableState.update { it.copy(syncState = SyncState.Offline, pendingCount = pendingCount) }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            reportError()
        }
    }

    private fun applyData(data: RemoteData, sync: SyncState) = mutableState.update { current ->
        current.copy(
            activities = data.activities, reminders = data.reminders, safety = data.safety,
            patientName = data.patient.name, patientAge = data.patient.age,
            preferredLanguage = data.patient.preferredLanguage,
            syncState = sync,
        )
    }

    companion object {
        fun factory(repository: PatientRepository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                PatientViewModel(repository) as T

            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(
                modelClass: Class<T>,
                extras: androidx.lifecycle.viewmodel.CreationExtras,
            ): T = PatientViewModel(repository, extras.createSavedStateHandle()) as T
        }
    }
}
