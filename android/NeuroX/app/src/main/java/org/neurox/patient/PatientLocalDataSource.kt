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
            cache.saveActivities(activities.map { item -> CachedActivityEntity(item.id, item.title, item.description, item.difficulty, fetchedAt) })
            cache.clearReminders()
            cache.saveReminders(reminders.map { item -> CachedReminderEntity(item.id, item.title, item.scheduledTime, item.completed, item.description, fetchedAt) })
            cache.saveSnapshot(CachedSnapshotEntity("activity-history", gson.toJson(history), fetchedAt))
            cache.saveSnapshot(CachedSnapshotEntity("emergency-contacts", gson.toJson(contacts), fetchedAt))
            cache.saveSnapshot(CachedSnapshotEntity("safety", gson.toJson(safety), fetchedAt))
        }
    }

    suspend fun load(): RemoteData? = withContext(Dispatchers.IO) {
        val cache = offlineDatabase.offlineCacheDao()
        val patient = cache.patient() ?: return@withContext null
        val history = cache.snapshot("activity-history")?.let { gson.fromJson<List<ActivityHistoryItem>>(it.payloadJson, object : TypeToken<List<ActivityHistoryItem>>() {}.type) } ?: emptyList()
        val contacts = cache.snapshot("emergency-contacts")?.let { gson.fromJson<List<EmergencyContactItem>>(it.payloadJson, object : TypeToken<List<EmergencyContactItem>>() {}.type) } ?: emptyList()
        val safety = cache.snapshot("safety")?.let { gson.fromJson(it.payloadJson, SafetyState::class.java) }
        RemoteData(
            Patient(patient.id, patient.name, patient.age, patient.preferredLanguage),
            cache.activities().map { ActivityItem(it.id, it.title, it.description, it.difficulty) },
            cache.reminders().map { ReminderItem(it.id, it.title, it.scheduledTime, it.completed, it.description) },
            history,
            contacts,
            safety
        )
    }

}
