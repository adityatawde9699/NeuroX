package org.neurox.patient

import android.content.Context
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import androidx.room.withTransaction
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import com.google.gson.reflect.TypeToken
import java.util.UUID

data class LoginRequest(val email: String, val password: String)
data class AuthResponse(@SerializedName("access_token") val accessToken: String, @SerializedName("refresh_token") val refreshToken: String, val user: User)
data class User(val id: String, val name: String, val email: String, val role: String)
data class Patient(val id: String, val name: String, val age: Int, val preferredLanguage: String)
data class ActivityItem(val id: String, val title: String, val description: String, val difficulty: Int)
data class ReminderItem(val id: String, val title: String, val scheduledTime: String, val completed: Boolean, val description: String? = null)
data class ActivityStartRequest(@SerializedName("user_id") val userId: String, @SerializedName("difficulty_level") val difficultyLevel: Int, @SerializedName("started_at") val startedAt: String, @SerializedName("event_id") val eventId: String, @SerializedName("offline_created") val offlineCreated: Boolean = false)
data class ActivityCompletionRequest(@SerializedName("user_id") val userId: String, @SerializedName("activity_id") val activityId: String, @SerializedName("started_at") val startedAt: String, @SerializedName("completed_at") val completedAt: String, val accuracy: Float, @SerializedName("response_time") val responseTime: Float, val attempts: Int, @SerializedName("completion_status") val completionStatus: String = "completed", @SerializedName("difficulty_level") val difficultyLevel: Int, @SerializedName("offline_created") val offlineCreated: Boolean = false, @SerializedName("event_id") val eventId: String)
data class SyncEventRequest(@SerializedName("event_id") val eventId: String, @SerializedName("event_type") val eventType: String, @SerializedName("patient_id") val patientId: String, val payload: Map<String, Any>)
data class SyncEventResult(@SerializedName("event_id") val eventId: String, val status: String, val result: Map<String, Any>? = null, val detail: String? = null)
data class SyncEventsResponse(val results: List<SyncEventResult>)
data class LocationUpdateRequest(val latitude: Double, val longitude: Double, @SerializedName("accuracy_m") val accuracyM: Double, @SerializedName("connection_state") val connectionState: String = "online", @SerializedName("captured_at") val capturedAt: String)
data class SafetyContact(val id: String, val name: String, val phone: String, val relationship: String, val priority: Int)
data class SafetyState(val patientId: String, val status: String, val contacts: List<SafetyContact> = emptyList())
data class ActivityHistoryItem(val id: String, val activityId: String, val startedAt: String, val completedAt: String?, val accuracy: Float?, val responseTime: Float?, val attempts: Int, val status: String, val difficulty: Int)
data class EmergencyContactItem(val id: String, val patientId: String, val name: String, val phone: String, val relationship: String, val priority: Int, val active: Boolean)
data class SosRequest(val message: String = "I need help. Please check on me.", @SerializedName("location_update_id") val locationUpdateId: String? = null)
data class SyncResult(val saved: Boolean = true, val message: String? = null, @SerializedName("next_difficulty") val nextDifficulty: Int? = null, @SerializedName("performance_score") val performanceScore: Float? = null)

interface NeuroXApi {
    @POST("auth/login") suspend fun login(@Body request: LoginRequest): AuthResponse
    @GET("patients/me") suspend fun patient(): Patient
    @GET("activities") suspend fun activities(): List<ActivityItem>
    @GET("patients/{patientId}/reminders") suspend fun reminders(@Path("patientId") patientId: String): List<ReminderItem>
    @GET("patients/{patientId}/activity-sessions") suspend fun activityHistory(@Path("patientId") patientId: String): List<ActivityHistoryItem>
    @GET("patients/{patientId}/emergency-contacts") suspend fun emergencyContacts(@Path("patientId") patientId: String): List<EmergencyContactItem>
    @PUT("reminders/{reminderId}") suspend fun completeReminder(@Path("reminderId") reminderId: String, @Body request: Map<String, Boolean>): ReminderItem
    @POST("activities/{activityId}/start") suspend fun startActivity(@Path("activityId") activityId: String, @Body request: ActivityStartRequest): Map<String, Any>
    @POST("activities/{activityId}/complete") suspend fun completeActivity(@Path("activityId") activityId: String, @Body request: ActivityCompletionRequest): SyncResult
    @POST("sync/events") suspend fun syncEvents(@Body events: List<SyncEventRequest>): SyncEventsResponse
    @GET("patients/{patientId}/safety") suspend fun safety(@Path("patientId") patientId: String): SafetyState
    @POST("patients/{patientId}/location-updates") suspend fun location(@Path("patientId") patientId: String, @Body request: LocationUpdateRequest): Map<String, Any>
    @POST("patients/{patientId}/sos-events") suspend fun sos(@Path("patientId") patientId: String, @Body request: SosRequest): Map<String, Any>
}

class NeuroXRepository(context: Context) {
    private val appContext = context.applicationContext
    private val preferences = context.getSharedPreferences("neurox_session", Context.MODE_PRIVATE)
    private val gson = com.google.gson.Gson()
    private val offlineDatabase = OfflineDatabase.get(context)
    private val api = Retrofit.Builder().baseUrl("http://10.0.2.2:8000/").addConverterFactory(GsonConverterFactory.create()).client(okhttp3.OkHttpClient.Builder().addInterceptor { chain ->
        val token = preferences.getString("access_token", null)
        chain.proceed(chain.request().newBuilder().apply { if (token != null) addHeader("Authorization", "Bearer $token") }.build())
    }.build()).build().create(NeuroXApi::class.java)

    suspend fun load(): RemoteData = withContext(Dispatchers.IO) {
        if (preferences.getString("access_token", null) == null) {
            val auth = api.login(LoginRequest("maya@neurox.demo", "NeuroXDemo!2026"))
            preferences.edit().putString("access_token", auth.accessToken).putString("patient_id", auth.user.id).apply()
        }
        syncPendingEvents()
        val patient = api.patient()
        val activities = api.activities()
        val reminders = api.reminders(patient.id)
        val history = api.activityHistory(patient.id)
        val contacts = api.emergencyContacts(patient.id)
        val safety = api.safety(patient.id)
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
        return@withContext RemoteData(patient, activities, reminders, history, contacts, safety)
    }

    suspend fun cachedData(): RemoteData? = withContext(Dispatchers.IO) {
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

    suspend fun markReminderComplete(reminderId: String) = api.completeReminder(reminderId, mapOf("completed" to true))
    suspend fun markReminderCompletedLocally(reminderId: String) = withContext(Dispatchers.IO) {
        offlineDatabase.offlineCacheDao().markReminderCompleted(reminderId)
    }
    suspend fun startActivity(activity: ActivityItem, eventId: String, startedAt: String, offline: Boolean) = api.startActivity(activity.id, ActivityStartRequest(userId = patientId(), difficultyLevel = activity.difficulty, startedAt = startedAt, eventId = eventId, offlineCreated = offline))
    suspend fun completeActivity(activity: ActivityItem, request: ActivityCompletionRequest) = api.completeActivity(activity.id, request)
    suspend fun queueActivityCompletion(request: ActivityCompletionRequest) = queue(
        SyncEventRequest(request.eventId, "activity_completion", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    suspend fun queueReminderUpdate(reminderId: String) = queue(
        SyncEventRequest(UUID.randomUUID().toString(), "reminder_update", patientId(), mapOf("reminder_id" to reminderId, "changes" to mapOf("completed" to true)))
    )
    suspend fun queueLocation(request: LocationUpdateRequest, eventId: String = UUID.randomUUID().toString()) = queue(
        SyncEventRequest(eventId, "location_update", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    suspend fun queueSos(request: SosRequest, eventId: String = UUID.randomUUID().toString()) = queue(
        SyncEventRequest(eventId, "sos_event", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    suspend fun sendSos(request: SosRequest) = api.sos(patientId(), request)
    suspend fun loadSafety() = api.safety(patientId())
    fun schedulePendingSync() = SyncWorker.enqueue(appContext)
    private suspend fun queue(event: SyncEventRequest) = withContext(Dispatchers.IO) {
        offlineDatabase.pendingSyncDao().insert(
            PendingSyncEntity(
                eventId = event.eventId,
                eventType = event.eventType,
                patientId = event.patientId,
                payloadJson = gson.toJson(event.payload),
                createdAt = System.currentTimeMillis(),
                status = "pending"
            )
        )
        SyncWorker.enqueue(appContext)
    }
    suspend fun syncPendingEvents(): SyncOutcome {
        val entities = offlineDatabase.pendingSyncDao().getAll()
        val pending = entities.map { entity ->
            SyncEventRequest(
                eventId = entity.eventId,
                eventType = entity.eventType,
                patientId = entity.patientId,
                payload = gson.fromJson(entity.payloadJson, object : TypeToken<Map<String, Any>>() {}.type)
            )
        }
        if (pending.isEmpty()) return SyncOutcome.Synced(0)
        val response = try {
            api.syncEvents(pending)
        } catch (error: java.io.IOException) {
            return SyncOutcome.Retry(error.message ?: "Network unavailable")
        }
        val completed = response.results.filter { it.status == "accepted" || it.status == "duplicate" }.map { it.eventId }.toSet()
        if (completed.isNotEmpty()) offlineDatabase.pendingSyncDao().delete(completed.toList())
        val rejectedResults = response.results.filter { it.status == "rejected" || it.status == "conflict" }
        if (rejectedResults.isNotEmpty()) {
            val message = rejectedResults.joinToString("; ") { it.detail ?: "Event was rejected by the server." }
            offlineDatabase.pendingSyncDao().markFailed(rejectedResults.map { it.eventId }, message)
        }
        val rejected = rejectedResults.size
        return if (rejected > 0) SyncOutcome.Partial(completed.size, rejected) else SyncOutcome.Synced(completed.size)
    }
    fun patientId(): String = preferences.getString("patient_id", "maya-demo") ?: "maya-demo"
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