package org.neurox.patient

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
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

val defaultActivities = listOf(
    ActivityItem("memory-match", "Memory Match", "Find two matching familiar objects.", 2),
    ActivityItem("object-recall", "Remember the Objects", "Look, listen, then remember.", 2),
    ActivityItem("pattern", "Pattern Completion", "Choose what comes next.", 2),
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
)

class PatientViewModel(private val repository: PatientRepository) : ViewModel() {
    private val completeActivity = CompleteActivity(repository)
    private val completeReminder = CompleteReminder(repository)
    private val sendHelp = SendHelp(repository)
    private val mutableState = MutableStateFlow(PatientUiState())
    val state = mutableState.asStateFlow()
    private var activeEventId: String? = null
    private var activeStartedAt: String? = null
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
            mutableState.update { it.copy(activeActivity = activity.id) }
        }
    }

    fun leaveActivity() {
        startJob?.cancel()
        activeEventId = null
        activeStartedAt = null
        mutableState.update { it.copy(activeActivity = null) }
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
        }
    }
}
