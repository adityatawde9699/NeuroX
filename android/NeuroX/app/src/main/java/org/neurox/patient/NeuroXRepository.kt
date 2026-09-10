package org.neurox.patient

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.google.gson.reflect.TypeToken
import java.util.UUID

class NeuroXRepository internal constructor(
    private val sessions: SecureSessionStore,
    private val local: PatientLocalDataSource,
    private val remote: PatientRemoteDataSource,
    private val enqueueSync: () -> Unit,
) : PatientRepository {
    private val gson = com.google.gson.Gson()
    private val offlineDatabase get() = local.database
    private val api get() = remote.api

    fun hasSession(): Boolean = sessions.read()?.accessToken != null
    fun configuredServer(): String = sessions.read()?.server ?: BuildConfig.DEFAULT_API_URL

    suspend fun signIn(server: String, email: String, password: String) = withContext(Dispatchers.IO) {
        val address = validatedServerAddress(server, BuildConfig.DEBUG)
        val previous = sessions.read()
        require(previous == null || previous.server == address) {
            "This device is linked to a different server. Use its original server to preserve offline records."
        }
        val auth = patientApi(address).login(LoginRequest(email.trim(), password))
        require(auth.user.role == "PATIENT") { "Use a patient account. Caregivers sign in on the web." }
        val cached = offlineDatabase.offlineCacheDao().patient()
        require((previous == null || previous.patientId == auth.user.id) && (cached == null || cached.id == auth.user.id)) {
            "This device belongs to another patient. Sign in with that patient's account."
        }
        require(previous != null || (cached == null && offlineDatabase.pendingSyncDao().countAll() == 0)) {
            "Offline records need recovery before this device can connect to a server."
        }
        val profile = patientApi(address).patientWithToken("Bearer ${auth.accessToken}")
        require(profile.id == auth.user.id) { "The patient profile does not match this account." }
        sessions.save(PatientSession(address, auth.user.id, auth.accessToken, auth.refreshToken))
    }

    override suspend fun load(): RemoteData = withContext(Dispatchers.IO) {
        check(hasSession()) { "Please sign in first." }
        syncPendingEvents()
        val fresh = remote.load()
        local.save(fresh)
        // Screens always observe the same representation that is available offline.
        local.load() ?: fresh
    }

    override suspend fun cachedData(): RemoteData? = local.load()

    override suspend fun markReminderComplete(reminderId: String) = api.updateReminder(reminderId, mapOf("status" to "done"))
    override suspend fun markReminderCompletedLocally(reminderId: String) = withContext(Dispatchers.IO) {
        offlineDatabase.offlineCacheDao().markReminderCompleted(reminderId)
        offlineDatabase.checkpointBackup()
    }
    override suspend fun updateReminderState(reminderId: String, status: String, snoozedUntil: String?) =
        api.updateReminder(reminderId, mapOf("status" to status, "snoozed_until" to snoozedUntil))
    override suspend fun updateReminderStateLocally(reminderId: String, status: String, snoozedUntil: String?) = withContext(Dispatchers.IO) {
        offlineDatabase.offlineCacheDao().updateReminderState(reminderId, status == "done", status, snoozedUntil)
        offlineDatabase.checkpointBackup()
    }
    override suspend fun queueReminderState(reminderId: String, status: String, snoozedUntil: String?) = queue(
        SyncEventRequest(UUID.randomUUID().toString(), "reminder_update", patientId(), mapOf("reminder_id" to reminderId, "changes" to mapOf("status" to status, "snoozed_until" to snoozedUntil)))
    )
    override suspend fun startActivity(activity: ActivityItem, eventId: String, startedAt: String, offline: Boolean) = api.startActivity(activity.id, ActivityStartRequest(userId = patientId(), difficultyLevel = activity.difficulty, startedAt = startedAt, eventId = eventId, offlineCreated = offline, contentVersion = activity.contentVersion))
    override suspend fun completeActivity(activity: ActivityItem, request: ActivityCompletionRequest) = api.completeActivity(activity.id, request)
    override suspend fun queueActivityCompletion(request: ActivityCompletionRequest) = queue(
        SyncEventRequest(request.eventId, "activity_completion", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    override suspend fun queueReminderUpdate(reminderId: String) = queue(
        SyncEventRequest(UUID.randomUUID().toString(), "reminder_update", patientId(), mapOf("reminder_id" to reminderId, "changes" to mapOf("completed" to true)))
    )
    suspend fun queueLocation(request: LocationUpdateRequest, eventId: String = UUID.randomUUID().toString()) = queue(
        SyncEventRequest(eventId, "location_update", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    override suspend fun queueSos(request: SosRequest, eventId: String) = queue(
        SyncEventRequest(eventId, "sos_event", patientId(), gson.fromJson(gson.toJson(request), object : TypeToken<Map<String, Any>>() {}.type))
    )
    override suspend fun sendSos(request: SosRequest) = api.sos(patientId(), request)
    override suspend fun privacy() = api.privacy()
    override suspend fun caregivers() = api.caregivers()
    override suspend fun setLocationSharing(enabled: Boolean) = api.setLocationSharing(LocationSharingRequest(enabled))
    override suspend fun revokeCaregiver(caregiverId: String) = api.revokeCaregiver(caregiverId)
    override suspend fun setConsent(purpose: String, granted: Boolean) = api.setConsent(ConsentUpdateRequest(purpose, granted))
    suspend fun loadSafety() = api.safety(patientId())
    override fun schedulePendingSync() = enqueueSync()
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
        offlineDatabase.checkpointBackup()
        enqueueSync()
    }
    suspend fun syncPendingEvents(): SyncOutcome {
        if (!hasSession()) return SyncOutcome.Retry("Sign in to sync your saved records.")
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
        } catch (error: retrofit2.HttpException) {
            return SyncOutcome.Retry(if (error.code() == 401) "Please sign in again." else "Server unavailable. Saved records will retry.")
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
    /** Returns the number of events currently waiting in the offline queue. */
    override suspend fun pendingEventCount(): Int = withContext(Dispatchers.IO) {
        offlineDatabase.pendingSyncDao().getAll().size
    }
    override fun patientId(): String = sessions.read()?.patientId ?: error("Please sign in first.")
}
