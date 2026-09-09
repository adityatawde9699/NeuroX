package org.neurox.patient

import java.util.UUID

interface PatientRepository {
    suspend fun load(): RemoteData
    suspend fun cachedData(): RemoteData?
    suspend fun pendingEventCount(): Int
    fun schedulePendingSync()
    fun patientId(): String
    suspend fun startActivity(activity: ActivityItem, eventId: String, startedAt: String, offline: Boolean): Map<String, Any>
    suspend fun completeActivity(activity: ActivityItem, request: ActivityCompletionRequest): SyncResult
    suspend fun queueActivityCompletion(request: ActivityCompletionRequest)
    suspend fun markReminderComplete(reminderId: String): ReminderItem
    suspend fun markReminderCompletedLocally(reminderId: String)
    suspend fun queueReminderUpdate(reminderId: String)
    suspend fun sendSos(request: SosRequest): Map<String, Any>
    suspend fun queueSos(request: SosRequest, eventId: String = UUID.randomUUID().toString())
}

data class RemoteData(
    val patient: Patient,
    val activities: List<ActivityItem>,
    val reminders: List<ReminderItem>,
    val history: List<ActivityHistoryItem> = emptyList(),
    val contacts: List<EmergencyContactItem> = emptyList(),
    val safety: SafetyState? = null
)

sealed interface SyncOutcome {
    data class Synced(val count: Int) : SyncOutcome
    data class Partial(val synced: Int, val failed: Int) : SyncOutcome
    data class Retry(val reason: String) : SyncOutcome
}
