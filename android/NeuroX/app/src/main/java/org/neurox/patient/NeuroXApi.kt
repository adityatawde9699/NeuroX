package org.neurox.patient

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

data class LoginRequest(val email: String, val password: String)
data class RefreshTokenRequest(@SerializedName("refresh_token") val refreshToken: String)
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
data class SafetySettingsSummary(val expectedReturnAt: String? = null)
data class SafetyState(val patientId: String, val status: String, val contacts: List<SafetyContact> = emptyList(), val settings: SafetySettingsSummary? = null)
data class ActivityHistoryItem(val id: String, val activityId: String, val startedAt: String, val completedAt: String?, val accuracy: Float?, val responseTime: Float?, val attempts: Int, val status: String, val difficulty: Int)
data class EmergencyContactItem(val id: String, val patientId: String, val name: String, val phone: String, val relationship: String, val priority: Int, val active: Boolean)
data class SosRequest(val message: String = "I need help. Please check on me.", @SerializedName("location_update_id") val locationUpdateId: String? = null)
data class SyncResult(val saved: Boolean = true, val message: String? = null, @SerializedName("next_difficulty") val nextDifficulty: Int? = null, @SerializedName("performance_score") val performanceScore: Float? = null)

interface NeuroXApi {
    @POST("auth/login") suspend fun login(@Body request: LoginRequest): AuthResponse
    @POST("auth/refresh") fun refresh(@Body request: RefreshTokenRequest): retrofit2.Call<AuthResponse>
    @GET("patients/me") suspend fun patientWithToken(@retrofit2.http.Header("Authorization") token: String): Patient
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
