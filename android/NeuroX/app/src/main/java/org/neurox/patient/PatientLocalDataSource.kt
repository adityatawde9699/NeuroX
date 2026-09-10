package org.neurox.patient

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.google.gson.reflect.TypeToken

/** Room adapter: stores a coherent snapshot in a single transaction. */
class PatientLocalDataSource(val database: OfflineDatabase) {
    private val offlineDatabase get() = database
    private val gson = com.google.gson.Gson()

    suspend fun save(data: RemoteData) = withContext(Dispatchers.IO) {
        val (patient, activities, reminders, history, contacts, safety) = data
        val fetchedAt = System.currentTimeMillis()
        offlineDatabase.withTransaction {
            val cache = offlineDatabase.offlineCacheDao()
            cache.savePatient(CachedPatientEntity(patient.id, patient.name, patient.age, patient.preferredLanguage, fetchedAt))
            cache.clearActivities()
            cache.saveActivities(activities.map { item -> CachedActivityEntity(item.id, item.title, item.description, item.difficulty, item.contentVersion, fetchedAt) })
            cache.clearReminders()
            cache.saveReminders(reminders.map { item -> CachedReminderEntity(item.id, item.title, item.scheduledTime, item.completed, item.description, item.type, item.repeatRule, item.enabled, item.status, item.snoozedUntil, item.timezoneName, fetchedAt) })
            cache.saveSnapshot(CachedSnapshotEntity("activity-history", gson.toJson(history), fetchedAt))
            cache.saveSnapshot(CachedSnapshotEntity("emergency-contacts", gson.toJson(contacts), fetchedAt))
            cache.saveSnapshot(CachedSnapshotEntity("safety", gson.toJson(safety), fetchedAt))
        }
        offlineDatabase.checkpointBackup()
    }

    suspend fun load(): RemoteData? = withContext(Dispatchers.IO) {
        val cache = offlineDatabase.offlineCacheDao()
        val patient = cache.patient() ?: return@withContext null
        val history = cache.snapshot("activity-history")?.let { gson.fromJson<List<ActivityHistoryItem>>(it.payloadJson, object : TypeToken<List<ActivityHistoryItem>>() {}.type) } ?: emptyList()
        val contacts = cache.snapshot("emergency-contacts")?.let { gson.fromJson<List<EmergencyContactItem>>(it.payloadJson, object : TypeToken<List<EmergencyContactItem>>() {}.type) } ?: emptyList()
        val safety = cache.snapshot("safety")?.let { gson.fromJson(it.payloadJson, SafetyState::class.java) }
        RemoteData(
            Patient(patient.id, patient.name, patient.age, patient.preferredLanguage),
            cache.activities().map { ActivityItem(it.id, it.title, it.description, it.difficulty, it.contentVersion) },
            cache.reminders().map { ReminderItem(it.id, it.title, it.scheduledTime, it.completed, it.description, it.type, it.repeatRule, it.enabled, it.status, it.snoozedUntil, it.timezoneName) },
            history,
            contacts,
            safety
        )
    }

}
